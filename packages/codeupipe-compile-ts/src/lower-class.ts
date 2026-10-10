import ts from "typescript";

import { CompileRefusal } from "./compile-refusal.ts";
import { isLiteral } from "./literal.ts";
import type { LoweredFunction, Made } from "./step-plan.ts";

export type Role = "Filter" | "Predicate" | "Tap";

const METHOD: Record<Role, string> = { Filter: "call", Predicate: "test", Tap: "observe" };
const WRITES = new Set(["insert", "remove", "merge"]);
const DATA = "Map<string, unknown>";

/** `DiscountFilter` gives `discount_filter`. */
export function snakeCase(className: string): string {
  return className.replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, "_").toLowerCase();
}

function isThis(node: ts.Node): boolean {
  return node.kind === ts.SyntaxKind.ThisKeyword;
}

type Setting = { value: string; type: string | undefined };

/**
 * The settings of one instance: each property of the class, with the value
 * that this `new ClassName(...)` gives it. Each value is a literal.
 */
function settingsOf(made: Made, where: string): Map<string, Setting> {
  const settings = new Map<string, Setting>();
  const node = made.ref.node;
  const constructor = node.members.find(ts.isConstructorDeclaration);

  for (const member of node.members) {
    if (!ts.isPropertyDeclaration(member)) continue;
    if (!ts.isIdentifier(member.name)) {
      throw new CompileRefusal(where, `the property \`${member.name.getText()}\` does not have a plain name`, "Give it a plain name");
    }
    if (member.initializer !== undefined && !isLiteral(member.initializer)) {
      throw new CompileRefusal(where, `the property \`${member.name.text}\` starts with a value that is not a literal`,
        "Start it with a literal, or take the value from the Payload");
    }
    settings.set(member.name.text, { value: member.initializer?.getText() ?? "undefined", type: member.type?.getText() });
  }
  if (constructor === undefined) {
    if (made.args.length > 0) throw new CompileRefusal(where, "the class has no constructor, but it is given arguments", "Remove the arguments");
    return settings;
  }

  const given = new Map<string, Setting>();
  constructor.parameters.forEach((parameter, index) => {
    if (!ts.isIdentifier(parameter.name) || parameter.dotDotDotToken !== undefined || ts.getModifiers(parameter)?.length) {
      throw new CompileRefusal(where, `the constructor parameter \`${parameter.getText()}\` is not a plain name`,
        "Use plain parameters, and assign each one to a property");
    }
    const argument = made.args[index];
    if (argument !== undefined && !isLiteral(argument)) {
      throw new CompileRefusal(where, `the argument \`${argument.getText()}\` is not a literal`,
        "Give literal settings (text, numbers, true, false, null, lists and objects of them)");
    }
    if (argument === undefined && parameter.initializer !== undefined && !isLiteral(parameter.initializer)) {
      throw new CompileRefusal(where, `the default of \`${parameter.name.text}\` is not a literal`, "Use a literal default");
    }
    given.set(parameter.name.text, {
      value: argument?.getText() ?? parameter.initializer?.getText() ?? "undefined", type: parameter.type?.getText(),
    });
  });
  if (made.args.length > constructor.parameters.length) {
    throw new CompileRefusal(where, "the class is given more arguments than its constructor has parameters", "Remove the extra arguments");
  }

  for (const statement of constructor.body?.statements ?? []) {
    const assignment = ts.isExpressionStatement(statement) && ts.isBinaryExpression(statement.expression)
      && statement.expression.operatorToken.kind === ts.SyntaxKind.EqualsToken ? statement.expression : undefined;
    const target = assignment !== undefined && ts.isPropertyAccessExpression(assignment.left) && isThis(assignment.left.expression)
      ? assignment.left.name.text : undefined;
    if (assignment === undefined || target === undefined) {
      throw new CompileRefusal(where, `the constructor does more than assign settings (\`${statement.getText().split("\n")[0]}\`)`,
        "Keep only statements of the form this.name = parameter");
    }
    const value = assignment.right;
    const fromParameter = ts.isIdentifier(value) ? given.get(value.text) : undefined;
    if (fromParameter === undefined && !isLiteral(value)) {
      throw new CompileRefusal(where, `the constructor computes the setting \`${target}\``,
        "Assign a parameter or a literal, and compute in the method");
    }
    settings.set(target, {
      value: fromParameter?.value ?? value.getText(),
      type: settings.get(target)?.type ?? fromParameter?.type,
    });
  }
  return settings;
}

/**
 * One step class as one plain function.
 *
 * The function takes the data as a `Map`. Each operation of the Payload
 * becomes an operation of the Map, and each `this.setting` becomes a
 * constant. A shape with no such form is refused.
 */
export function lowerClass(made: Made, role: Role, name: string): LoweredFunction {
  const node = made.ref.node;
  const where = made.ref.name;
  const source = made.ref.source;
  const methodName = METHOD[role];

  if ((node.heritageClauses ?? []).some((clause) => clause.token === ts.SyntaxKind.ExtendsKeyword)) {
    throw new CompileRefusal(where, "the class extends another class", "Put the code of the step in one class");
  }
  const method = node.members.find((member): member is ts.MethodDeclaration =>
    ts.isMethodDeclaration(member) && member.name.getText() === methodName);
  if (method === undefined || method.body === undefined) {
    throw new CompileRefusal(where, `the class has no ${methodName}(payload) method`, `A ${role} has ${methodName}(payload)`);
  }
  const isAsync = (ts.getModifiers(method) ?? []).some((modifier) => modifier.kind === ts.SyntaxKind.AsyncKeyword);
  if (method.asteriskToken !== undefined) {
    throw new CompileRefusal(where, `${methodName} is a generator`, "Make it a plain method");
  }
  if (isAsync && role === "Predicate") {
    throw new CompileRefusal(where, "test is async", "A Predicate gives true or false at once. Make test sync");
  }
  const parameter = method.parameters[0];
  if (method.parameters.length !== 1 || parameter === undefined || !ts.isIdentifier(parameter.name)) {
    throw new CompileRefusal(where, `${methodName} does not take one plain parameter`, `Write ${methodName}(payload)`);
  }
  const data = parameter.name.text;
  const settings = settingsOf(made, where);
  const used = new Set<string>();
  const helpers = new Set<string>();
  let returns = 0;
  let depth = 0; // the number of functions inside the method that the visitor is in

  /** The parameter itself, or a chain of writes on it: `payload.insert(..).remove(..)`. */
  const isData = (expression: ts.Expression): boolean => {
    if (ts.isIdentifier(expression)) return expression.text === data;
    return ts.isCallExpression(expression) && ts.isPropertyAccessExpression(expression.expression)
      && WRITES.has(expression.expression.name.text) && isData(expression.expression.expression);
  };

  const refuse = (what: string, hint: string): never => {
    throw new CompileRefusal(where, what, hint);
  };

  const transformer: ts.TransformerFactory<ts.Block> = (context) => {
    const factory = context.factory;
    const call = (helper: string, typeArguments: readonly ts.TypeNode[] | undefined, args: ts.Expression[]) => {
      helpers.add(helper);
      return factory.createCallExpression(factory.createIdentifier(helper), typeArguments, args);
    };

    const visit = (node: ts.Node): ts.Node => {
      if (ts.isIdentifier(node) && node.text.startsWith("cup_")) {
        return refuse(`the name \`${node.text}\` starts with cup_`, "The compiler uses names that start with cup_. Use another name");
      }

      // this.setting
      if (ts.isPropertyAccessExpression(node) && isThis(node.expression)) {
        const setting = node.name.text;
        if (!settings.has(setting)) {
          return refuse(`${methodName} uses \`this.${setting}\`, which is not a property with a literal value`,
            "Use a setting of the instance, or a function that the file imports");
        }
        const parent = node.parent;
        const isWritten = (ts.isBinaryExpression(parent) && parent.left === node
          && parent.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && parent.operatorToken.kind <= ts.SyntaxKind.LastAssignment)
          || ts.isPrefixUnaryExpression(parent) || ts.isPostfixUnaryExpression(parent);
        if (isWritten) {
          return refuse(`${methodName} assigns to \`this.${setting}\``, "A step keeps nothing between runs. Put the value in the Payload");
        }
        used.add(setting);
        return factory.createIdentifier(`${name}_${setting}`);
      }
      if (isThis(node)) {
        return refuse(`${methodName} uses \`this\` for more than a setting`, "Read settings as this.name, and use no other member");
      }

      // payload.operation(...)
      if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression) && isData(node.expression.expression)) {
        const operation = node.expression.name.text;
        const inner = node.expression.expression;
        const receiver = ts.isIdentifier(inner) ? inner : (visit(inner) as ts.Expression);
        const args = node.arguments.map((argument) => visit(argument) as ts.Expression);
        if (WRITES.has(operation) && role !== "Filter") {
          return refuse(`${methodName} writes to the Payload (\`${data}.${operation}\`)`, "Only a Filter writes. Put the write in a Filter");
        }
        if (operation === "insert" && args.length === 2) {
          return factory.createCallExpression(factory.createPropertyAccessExpression(receiver, "set"), undefined, args);
        }
        if (operation === "remove" && args.length === 1) return call("cup_remove", undefined, [receiver, ...args]);
        if (operation === "get" && (args.length === 1 || args.length === 2)) {
          return call("cup_get", node.typeArguments, [receiver, ...args]);
        }
        if (operation === "has" && args.length === 1) {
          return factory.createCallExpression(factory.createPropertyAccessExpression(receiver, "has"), undefined, args);
        }
        if (operation === "toDict" && args.length === 0) {
          return factory.createCallExpression(factory.createPropertyAccessExpression(factory.createIdentifier("Object"), "fromEntries"),
            undefined, [receiver]);
        }
        if (operation === "merge" && node.arguments.length === 1) {
          const other = node.arguments[0];
          if (other !== undefined && ts.isNewExpression(other) && other.expression.getText() === "Payload"
            && (other.arguments?.length ?? 0) <= 1) {
            const map = other.arguments?.[0];
            return call("cup_merge", undefined, [receiver, map === undefined ? factory.createObjectLiteralExpression() : (visit(map) as ts.Expression)]);
          }
          return refuse(`${methodName} merges a Payload that it did not make there`, "Write payload.merge(new Payload(map))");
        }
        return refuse(`${methodName} uses \`${data}.${operation}\` in a form that has no plain code`,
          "The operations are get, has, insert, remove, merge(new Payload(map)) and toDict");
      }

      // the payload itself, in any other place
      if (ts.isIdentifier(node) && node.text === data) {
        const parent = node.parent;
        const isName = (ts.isPropertyAccessExpression(parent) && parent.name === node)
          || (ts.isPropertyAssignment(parent) && parent.name === node)
          || ((ts.isMethodDeclaration(parent) || ts.isPropertyDeclaration(parent)) && parent.name === node);
        if (isName) return node;
        if (ts.isReturnStatement(parent) && depth === 0) return node;
        if (ts.isPropertyAccessExpression(parent) && parent.expression === node) {
          return refuse(`${methodName} uses \`${data}.${parent.name.text}\``,
            "The operations are get, has, insert, remove, merge(new Payload(map)) and toDict");
        }
        return refuse(`${methodName} gives the Payload to other code, or gives it another name`,
          "Use the Payload only through its operations, and return it");
      }

      if (ts.isReturnStatement(node) && depth === 0 && role === "Filter") {
        returns += 1;
        if (node.expression === undefined || !isData(node.expression)) {
          return refuse("call returns something that is not the Payload it was given",
            "Return the payload, or a write on it: return payload.insert(key, value)");
        }
      }

      if (ts.isFunctionLike(node) || ts.isClassLike(node)) {
        depth += 1;
        const result = ts.visitEachChild(node, visit, context);
        depth -= 1;
        return result;
      }
      return ts.visitEachChild(node, visit, context);
    };
    return (body) => ts.visitEachChild(body, visit, context);
  };

  const result = ts.transform(method.body, [transformer]);
  const body = result.transformed[0];
  if (body === undefined) throw new CompileRefusal(where, "the method has no body", "Give it a body");
  const last = method.body.statements[method.body.statements.length - 1];
  if (role === "Filter" && returns === 0 && !(last !== undefined && ts.isThrowStatement(last))) {
    refuse("call does not return the Payload", "End call with return payload");
  }
  const printed = ts.createPrinter({ removeComments: false }).printNode(ts.EmitHint.Unspecified, body, source.tree);
  result.dispose();

  const returnType = role === "Predicate" ? ": boolean" : "";
  const code = `${isAsync ? "async " : ""}function ${name}(${data}: ${DATA})${returnType} ${printed}`;
  const consts = [...used].map((setting) => {
    const { value, type } = settings.get(setting) ?? { value: "undefined", type: undefined };
    return `const ${name}_${setting}${type === undefined ? "" : `: ${type}`} = ${value};`;
  });

  // The identifiers that the code uses, to find which imports it needs.
  const names = new Set<string>(helpers);
  const scan = ts.createSourceFile("lowered.ts", [...consts, code].join("\n"), ts.ScriptTarget.Latest, true);
  const collect = (inner: ts.Node) => {
    if (ts.isIdentifier(inner) && !(ts.isPropertyAccessExpression(inner.parent) && inner.parent.name === inner)) {
      names.add(inner.text);
    }
    ts.forEachChild(inner, collect);
  };
  collect(scan);

  return { name, consts, code, isAsync, names, source };
}

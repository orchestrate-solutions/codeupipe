// Finds anonymous pipeline steps in TypeScript source, for
// packages/codeupipe-lint/codeupipe_lint/anonymous_steps/analyze_typescript.py. Uses the TypeScript compiler
// API (parser + binder/checker for name resolution); runs under bun or node.
//
// Usage: <bun|node> anonymous_steps.mjs <path to the typescript package>
// Input: file paths, one per line, on stdin. Output: one JSON object per
// finding per line: {"path","line","col","rule","role","what","call_line"}.
//
// A step is an argument of a method named addFilter, addTap, addPipeline or
// addParallel (any receiver; array elements for addParallel), or of
// `new Valve(...)`. It is anonymous when it is, or a `const` / declaration it
// names is:
//
//   CUP-A001 an arrow function or a function expression
//   CUP-A002 a function declared inside a function
//   CUP-A003 a class declared inside a function, or an instance of one
//   CUP-A004 a class expression or an object literal
//   CUP-A005 a plain `new Pipeline()` (or a method chain on one)
//   CUP-A008 a named function as a Valve predicate (predicates are objects)
//
// or the result of calling a function in the same file that returns one of
// those (a closure factory). Calls on a TypedPipeline (the typed variant,
// which still takes step names) are out of scope.

import { createRequire } from "node:module";
import * as fs from "node:fs";

const require = createRequire(import.meta.url);
const ts = require(process.argv[2]);

// Pipelines that still take hand-written step names (the typed variant):
// step identity does not apply to their add calls.
const NAMED_STEP_PIPELINES = new Set(["TypedPipeline"]);

const STEP_METHODS = { addFilter: "Filter", addTap: "Tap", addPipeline: "Nested pipeline", addParallel: "Parallel filter" };

const FUNCTION_KINDS = new Set([
  ts.SyntaxKind.FunctionDeclaration, ts.SyntaxKind.FunctionExpression, ts.SyntaxKind.ArrowFunction,
  ts.SyntaxKind.MethodDeclaration, ts.SyntaxKind.Constructor, ts.SyntaxKind.GetAccessor,
  ts.SyntaxKind.SetAccessor,
]);

function enclosingFunction(node) {
  for (let n = node.parent; n; n = n.parent) if (FUNCTION_KINDS.has(n.kind)) return n;
  return undefined;
}

function functionLabel(fn) {
  if (fn.name && ts.isIdentifier(fn.name)) return `${fn.name.text}()`;
  if (fn.kind === ts.SyntaxKind.Constructor) return "a constructor";
  if (fn.parent && ts.isVariableDeclaration(fn.parent) && ts.isIdentifier(fn.parent.name)) return `${fn.parent.name.text}()`;
  return "an anonymous function";
}

function unwrap(e) {
  while (e && (ts.isParenthesizedExpression(e) || ts.isAsExpression(e) || ts.isNonNullExpression(e) ||
    ts.isTypeAssertionExpression(e) || (ts.isSatisfiesExpression && ts.isSatisfiesExpression(e)))) e = e.expression;
  return e;
}

function calleeName(e) {
  e = unwrap(e);
  if (ts.isIdentifier(e)) return e.text;
  if (ts.isPropertyAccessExpression(e)) return e.name.text;
  return "";
}

function isPlainPipeline(e) {
  e = unwrap(e);
  if (ts.isNewExpression(e)) return calleeName(e.expression) === "Pipeline" && (!e.arguments || e.arguments.length === 0);
  if (ts.isCallExpression(e) && ts.isPropertyAccessExpression(e.expression)) return isPlainPipeline(e.expression.expression);
  return false;
}

function analyze(checker, sf) {
  const out = [];
  const seen = new Set();

  function declarationOf(id) {
    const sym = checker.getSymbolAtLocation(id);
    if (!sym || !sym.declarations || sym.declarations.length === 0) return undefined;
    if (sym.flags & ts.SymbolFlags.Alias) return undefined; // imported: top-level elsewhere
    return sym.declarations[0];
  }

  // -> {rule, subject?, noun} | undefined
  function describe(expr, visiting) {
    const e = unwrap(expr);
    if (!e) return undefined;
    if (ts.isArrowFunction(e)) return { rule: "CUP-A001", noun: "an arrow function" };
    if (ts.isFunctionExpression(e)) return { rule: "CUP-A001", noun: "a function expression" };
    if (ts.isClassExpression(e)) return { rule: "CUP-A004", noun: "a class expression" };
    if (ts.isObjectLiteralExpression(e)) return { rule: "CUP-A004", noun: "an object literal" };
    if (isPlainPipeline(e)) return { rule: "CUP-A005", noun: "a plain new Pipeline()" };
    if (ts.isNewExpression(e)) {
      const target = unwrap(e.expression);
      if (ts.isClassExpression(target)) return { rule: "CUP-A004", noun: "an instance of a class expression" };
      if (ts.isIdentifier(target)) {
        const decl = declarationOf(target);
        if (decl && ts.isClassDeclaration(decl)) {
          const fn = enclosingFunction(decl);
          if (fn) return { rule: "CUP-A003", noun: `an instance of ${target.text}, a class declared inside ${functionLabel(fn)}` };
        }
      }
      return undefined;
    }
    if (ts.isIdentifier(e)) {
      const got = describeDeclaration(declarationOf(e), visiting);
      return got ? { rule: got.rule, subject: e.text, noun: got.noun } : undefined;
    }
    if (ts.isCallExpression(e) && ts.isIdentifier(unwrap(e.expression))) {
      const callee = unwrap(e.expression);
      const decl = declarationOf(callee);
      let fn;
      if (decl && ts.isFunctionDeclaration(decl)) fn = decl;
      else if (decl && ts.isVariableDeclaration(decl) && decl.initializer && isConst(decl)) {
        const init = unwrap(decl.initializer);
        if (ts.isArrowFunction(init) || ts.isFunctionExpression(init)) fn = init;
      }
      if (fn && !visiting.has(fn)) {
        const got = returned(fn, new Set([...visiting, fn]));
        if (got) {
          const shown = got.subject ? `\`${got.subject}\`, ${got.noun}` : got.noun;
          return { rule: got.rule, noun: `the result of ${callee.text}(), which returns ${shown}` };
        }
      }
    }
    return undefined;
  }

  function isConst(decl) {
    const list = decl.parent;
    return list && ts.isVariableDeclarationList(list) && (list.flags & ts.NodeFlags.Const) !== 0;
  }

  function describeDeclaration(decl, visiting) {
    if (!decl) return undefined;
    if (ts.isClassDeclaration(decl)) {
      const fn = enclosingFunction(decl);
      return fn ? { rule: "CUP-A003", noun: `a class declared inside ${functionLabel(fn)}` } : undefined;
    }
    if (ts.isFunctionDeclaration(decl)) {
      const fn = enclosingFunction(decl);
      return fn ? { rule: "CUP-A002", noun: `a function declared inside ${functionLabel(fn)}` } : undefined;
    }
    if (ts.isVariableDeclaration(decl) && decl.initializer && isConst(decl) && !visiting.has(decl)) {
      const got = describe(decl.initializer, new Set([...visiting, decl]));
      return got ? { rule: got.rule, noun: got.subject ? `\`${got.subject}\`, ${got.noun}` : got.noun } : undefined;
    }
    return undefined;
  }

  function returned(fn, visiting) {
    if (!fn.body) return undefined;
    if (!ts.isBlock(fn.body)) return describe(fn.body, visiting); // expression-bodied arrow
    let got;
    const visit = (n) => {
      if (got) return;
      if (n !== fn && FUNCTION_KINDS.has(n.kind)) return; // not this function's returns
      if (ts.isClassDeclaration(n) || ts.isClassExpression(n)) return;
      if (ts.isReturnStatement(n) && n.expression) {
        got = describe(n.expression, visiting);
        return;
      }
      ts.forEachChild(n, visit);
    };
    ts.forEachChild(fn.body, visit);
    return got;
  }

  function report(arg, role, call) {
    let got = describe(arg, new Set());
    if (!got && role === "Valve predicate" && ts.isIdentifier(unwrap(arg))) {
      const decl = declarationOf(unwrap(arg));
      if (decl && ts.isFunctionDeclaration(decl)) {
        got = { rule: "CUP-A008", subject: unwrap(arg).text, noun: "a function, not a predicate object" };
      }
    }
    if (!got) return;
    if (got.rule === "CUP-A005" && role === "Valve predicate") return;
    const start = arg.getStart(sf);
    const pos = sf.getLineAndCharacterOfPosition(start);
    const key = `${start}:${got.rule}`;
    if (seen.has(key)) return;
    seen.add(key);
    const what = got.subject ? `\`${got.subject}\` is ${got.noun}` : `is ${got.noun}`;
    out.push({
      path: sf.fileName, line: pos.line + 1, col: pos.character + 1, rule: got.rule, role, what,
      call_line: sf.getLineAndCharacterOfPosition(call.getStart(sf)).line + 1,
    });
  }

  // The constructor a receiver was built with: new X(), a method chain on
  // it, or a const bound to either.
  function receiverClass(expr, depth = 0) {
    const e = unwrap(expr);
    if (!e || depth > 20) return "";
    if (ts.isNewExpression(e)) return calleeName(e.expression);
    if (ts.isCallExpression(e) && ts.isPropertyAccessExpression(e.expression)) return receiverClass(e.expression.expression, depth + 1);
    if (ts.isIdentifier(e)) {
      const decl = declarationOf(e);
      if (decl && ts.isVariableDeclaration(decl) && decl.initializer) return receiverClass(decl.initializer, depth + 1);
    }
    return "";
  }

  const visit = (node) => {
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
      const role = STEP_METHODS[node.expression.name.text];
      if (role && !NAMED_STEP_PIPELINES.has(receiverClass(node.expression.expression))) {
        for (const arg of node.arguments) {
          const a = unwrap(arg);
          if (ts.isArrayLiteralExpression(a)) a.elements.forEach((el) => report(el, role, node));
          else report(arg, role, node);
        }
      }
    } else if (ts.isNewExpression(node) && calleeName(node.expression) === "Valve" && node.arguments) {
      const args = node.arguments;
      args.forEach((arg, i) => report(arg, i === args.length - 1 ? "Valve predicate" : "Valve inner filter", node));
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return out;
}

const paths = fs.readFileSync(0, "utf8").split("\n").map((s) => s.trim()).filter(Boolean);
const program = ts.createProgram(paths, {
  allowJs: true, noResolve: true, noLib: true, types: [], noEmit: true, skipLibCheck: true,
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.Preserve,
});
const checker = program.getTypeChecker();
const lines = [];
for (const path of paths) {
  const sf = program.getSourceFile(path);
  if (!sf) {
    lines.push(JSON.stringify({ path, line: 1, col: 1, rule: "CUP-A000", role: "File", what: "could not be read", call_line: 1 }));
    continue;
  }
  const diags = program.getSyntacticDiagnostics(sf);
  if (diags.length > 0) {
    const d = diags[0];
    const pos = sf.getLineAndCharacterOfPosition(d.start ?? 0);
    const msg = ts.flattenDiagnosticMessageText(d.messageText, " ");
    lines.push(JSON.stringify({ path, line: pos.line + 1, col: pos.character + 1, rule: "CUP-A000", role: "File",
      what: `is not valid TypeScript (${msg})`, call_line: pos.line + 1 }));
    continue;
  }
  for (const f of analyze(checker, sf)) lines.push(JSON.stringify({ ...f, path }));
}
process.stdout.write(lines.length ? lines.join("\n") + "\n" : "");

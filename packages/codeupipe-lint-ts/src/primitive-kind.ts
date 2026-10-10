import ts from "typescript";

export type PrimitiveKind = "Pipeline" | "Hook" | "Filter" | "Tap" | "Predicate";

const BY_METHOD: Array<[string, PrimitiveKind]> = [["call", "Filter"], ["observe", "Tap"], ["test", "Predicate"]];
const BY_INTERFACE: Record<string, PrimitiveKind> = { Filter: "Filter", Tap: "Tap", Predicate: "Predicate" };
const HOOK_METHODS = ["before", "after", "onError"];

function heritage(node: ts.ClassLikeDeclaration, token: ts.SyntaxKind): string[] {
  const names: string[] = [];
  for (const clause of node.heritageClauses ?? []) {
    if (clause.token !== token) continue;
    for (const type of clause.types) {
      const expression = type.expression;
      if (ts.isIdentifier(expression)) names.push(expression.text);
      else if (ts.isPropertyAccessExpression(expression)) names.push(expression.name.text);
    }
  }
  return names;
}

/** The methods of a class, by name. */
export function methodsOf(node: ts.ClassLikeDeclaration): Map<string, ts.MethodDeclaration> {
  const methods = new Map<string, ts.MethodDeclaration>();
  for (const member of node.members) {
    if (ts.isMethodDeclaration(member) && ts.isIdentifier(member.name)) methods.set(member.name.text, member);
  }
  return methods;
}

/** One parameter that the caller must give: not optional, no default, not a rest parameter. */
function takesOnlyThePayload(method: ts.MethodDeclaration): boolean {
  const [parameter, ...others] = method.parameters;
  return parameter !== undefined && others.length === 0 && parameter.dotDotDotToken === undefined
    && parameter.questionToken === undefined && parameter.initializer === undefined;
}

/**
 * Which primitive a class is, read from its shape. Undefined for any other class.
 *
 * - `extends Pipeline` is a Pipeline.
 * - `extends Hook`, or the methods `before`, `after` and `onError`, is a Hook.
 * - `implements Filter`, or `call` with one parameter, is a Filter.
 * - `implements Tap`, or `observe` with one parameter, is a Tap.
 * - `implements Predicate`, or `test` with one parameter, is a Predicate.
 *
 * `call`, `observe` and `test` count only with exactly one required
 * parameter, so an unrelated `call(a, b)` or `observe(options = {})` is not
 * mistaken for a step.
 */
export function primitiveKind(node: ts.ClassLikeDeclaration): PrimitiveKind | undefined {
  const methods = methodsOf(node);
  const bases = heritage(node, ts.SyntaxKind.ExtendsKeyword);
  if (bases.includes("Pipeline")) return "Pipeline";
  if (bases.includes("Hook") || HOOK_METHODS.every((name) => methods.has(name))) return "Hook";
  for (const name of heritage(node, ts.SyntaxKind.ImplementsKeyword)) {
    const kind = BY_INTERFACE[name];
    if (kind !== undefined) return kind;
  }
  for (const [name, kind] of BY_METHOD) {
    const method = methods.get(name);
    if (method !== undefined && takesOnlyThePayload(method)) return kind;
  }
  return undefined;
}

/** A test file, or a file under a `tests` directory. */
export function isTestFile(path: string): boolean {
  const parts = path.replaceAll("\\", "/").split("/");
  const name = parts[parts.length - 1] ?? "";
  return parts.slice(0, -1).some((part) => part === "tests" || part === "__tests__")
    || /\.(test|spec)\.[cm]?tsx?$/.test(name);
}

/** The classes at the top level of a file that are primitives. */
export function topLevelPrimitives(tree: ts.SourceFile): Array<{ node: ts.ClassDeclaration; name: string; kind: PrimitiveKind }> {
  const found: Array<{ node: ts.ClassDeclaration; name: string; kind: PrimitiveKind }> = [];
  for (const statement of tree.statements) {
    if (!ts.isClassDeclaration(statement) || statement.name === undefined) continue;
    const kind = primitiveKind(statement);
    if (kind !== undefined) found.push({ node: statement, name: statement.name.text, kind });
  }
  return found;
}

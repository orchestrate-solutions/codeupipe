/**
 * Step identity, build side (conformance/API.md, "Step identity").
 *
 * JavaScript has no runtime record of which module a class came from, and
 * minifiers rename classes, so TypeScript cannot derive a step's identity at
 * runtime the way Python, Go, Rust, Kotlin and C# do. Instead a build step
 * stamps it: every top-level class and function declaration gets
 *
 *     Object.defineProperty(Name, Symbol.for("cup.identity"), { value: "<label>#Name" })
 *
 * appended to its module. The label is the package name plus the source
 * path without extension (`@codeupipe/core/src/valve`), so it is the same
 * under every toolchain and every working directory, and a string literal
 * survives minification.
 *
 * Only top-level declarations are stamped. A class or function defined inside
 * another function, an arrow function, or an object literal gets no stamp, and
 * the runtime refuses an unstamped step (step_identity.ts): TypeScript's
 * runtime enforcement of "no anonymous steps" is complete.
 *
 * Adapters: vite_plugin.ts (vitest, vite), bun_preload.ts (bun run),
 * stamp_dist.ts (tsc output, via source maps).
 */

import ts from "typescript";
import * as fs from "node:fs";
import * as path from "node:path";

export const IDENTITY_KEY = "cup.identity";
const MARKER = "/* codeupipe step identity (identity/stamp.ts) */";
const MARKER_INLINE = MARKER;

const packageCache = new Map<string, { root: string; name: string }>();

/** The nearest package.json above `file` (its dir and name), else the git root. */
function packageOf(file: string): { root: string; name: string } {
  let dir = path.dirname(path.resolve(file));
  const start = dir;
  const cached = packageCache.get(start);
  if (cached) return cached;
  let gitRoot: string | null = null;
  for (;;) {
    const pkg = path.join(dir, "package.json");
    if (fs.existsSync(pkg)) {
      const name = JSON.parse(fs.readFileSync(pkg, "utf8")).name ?? path.basename(dir);
      const found = { root: dir, name };
      packageCache.set(start, found);
      return found;
    }
    if (gitRoot === null && fs.existsSync(path.join(dir, ".git"))) gitRoot = dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  const root = gitRoot ?? process.cwd();
  const found = { root, name: path.basename(root) };
  packageCache.set(start, found);
  return found;
}

/** `<package name>/<path from the package root, no extension>` for a source file. */
export function labelFor(file: string): string {
  const { root, name } = packageOf(file);
  const rel = path.relative(root, path.resolve(file)).split(path.sep).join("/");
  return `${name}/${rel.replace(/\.[cm]?[jt]sx?$/, "")}`;
}

function scriptKind(file: string): ts.ScriptKind {
  if (/\.tsx$/.test(file)) return ts.ScriptKind.TSX;
  if (/\.[cm]?ts$/.test(file)) return ts.ScriptKind.TS;
  if (/\.jsx$/.test(file)) return ts.ScriptKind.JSX;
  return ts.ScriptKind.JS;
}

function isAmbient(node: ts.Node): boolean {
  return (ts.getCombinedModifierFlags(node as ts.Declaration) & ts.ModifierFlags.Ambient) !== 0;
}

type Declaration = { name: string; kind: "class" | "function"; end: number };

function declarations(code: string, file: string): Declaration[] {
  const source = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, false, scriptKind(file));
  const found: Declaration[] = [];
  const seen = new Set<string>();
  for (const statement of source.statements) {
    let kind: Declaration["kind"] | null = null;
    if (ts.isClassDeclaration(statement) && statement.name && !isAmbient(statement)) kind = "class";
    else if (ts.isFunctionDeclaration(statement) && statement.name && statement.body && !isAmbient(statement)) {
      kind = "function";
    }
    if (kind && statement.name && !seen.has(statement.name.text)) {
      seen.add(statement.name.text);
      found.push({ name: statement.name.text, kind, end: statement.end });
    }
  }
  return found;
}

/** Names of the module's top-level class and function declarations. */
export function topLevelDeclarations(code: string, file: string): string[] {
  return declarations(code, file).map((d) => d.name);
}

/** Where code may be prepended: after a shebang and any directive prologue. */
function prologueEnd(code: string, file: string): number {
  const source = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, false, scriptKind(file));
  let end = code.startsWith("#!") ? code.indexOf("\n") + 1 : 0;
  for (const statement of source.statements) {
    if (ts.isExpressionStatement(statement) && ts.isStringLiteral(statement.expression)) end = statement.end;
    else break;
  }
  return end;
}

/**
 * `code` with an identity stamp for each top-level declaration.
 *
 * Stamps must exist before the module's own top-level code uses a
 * declaration (a pipeline built at module level). So a class is stamped
 * right after its declaration, and a function (hoisted) at the top of the
 * module. Both are inserted without newlines: no line moves, so source maps
 * and stack-trace line numbers stay exact.
 */
export function stampSource(code: string, file: string, label: string = labelFor(file)): string {
  if (code.includes(MARKER)) return code; // already stamped (e.g. tsc output run through a bundler)
  const found = declarations(code, file);
  if (found.length === 0) return code;
  const key = JSON.stringify(IDENTITY_KEY);
  const stamp = (name: string) =>
    `;Object.defineProperty(${name}, Symbol.for(${key}), { value: ${JSON.stringify(`${label}#${name}`)} });`;
  const edits: Array<[number, string]> = found
    .filter((d) => d.kind === "class")
    .map((d) => [d.end, stamp(d.name)] as [number, string]);
  const functions = found.filter((d) => d.kind === "function").map((d) => stamp(d.name)).join("");
  edits.push([prologueEnd(code, file), `${MARKER_INLINE}${functions}`]);
  let out = code;
  for (const [at, text] of edits.sort((a, b) => b[0] - a[0])) out = out.slice(0, at) + text + out.slice(at);
  return out;
}

/** Whether a module path should be stamped: source, not dependencies. */
export function shouldStamp(file: string): boolean {
  return /\.[cm]?[jt]sx?$/.test(file) && !file.includes(`${path.sep}node_modules${path.sep}`) && !/\.d\.ts$/.test(file);
}

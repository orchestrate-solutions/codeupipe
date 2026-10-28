import { existsSync, readFileSync, statSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";

import ts from "typescript";

import { CompileRefusal } from "./compile-refusal.ts";

/** One parsed file. */
export type Source = { path: string; tree: ts.SourceFile };

/** A class, and the file that it is in. */
export type ClassRef = { source: Source; node: ts.ClassDeclaration; name: string };

/** One name that a file imports. `imported` is the exported name, "default" or "*". */
export type ImportBinding = {
  local: string;
  imported: string;
  specifier: string;
  /** The file, for a relative import. Undefined for a package. */
  file: string | undefined;
  typeOnly: boolean;
};

const cache = new Map<string, Source>();

export function loadSource(path: string): Source {
  const absolute = resolve(path);
  let source = cache.get(absolute);
  if (source === undefined) {
    const text = readFileSync(absolute, "utf8");
    source = { path: absolute, tree: ts.createSourceFile(absolute, text, ts.ScriptTarget.Latest, true) };
    cache.set(absolute, source);
  }
  return source;
}

/** Forget the files that were read. For a tool that compiles a file again after it changes. */
export function clearSources(): void {
  cache.clear();
}

function isFile(path: string): boolean {
  return existsSync(path) && statSync(path).isFile();
}

/** The file of a relative import, or undefined for a package. */
function resolveModule(from: string, specifier: string): string | undefined {
  if (!specifier.startsWith(".") && !specifier.startsWith("/")) return undefined;
  const base = resolve(dirname(from), specifier);
  const candidates = [base, base.replace(/\.js$/, ".ts"), base.replace(/\.mjs$/, ".mts"), base + ".ts", base + ".tsx",
    join(base, "index.ts")];
  return candidates.find(isFile);
}

/** The names that a file imports. */
export function importsOf(source: Source): ImportBinding[] {
  const found: ImportBinding[] = [];
  for (const statement of source.tree.statements) {
    if (!ts.isImportDeclaration(statement) || !ts.isStringLiteral(statement.moduleSpecifier)) continue;
    const clause = statement.importClause;
    if (clause === undefined) continue;
    const specifier = statement.moduleSpecifier.text;
    const file = resolveModule(source.path, specifier);
    const base = { specifier, file };
    if (clause.name !== undefined) {
      found.push({ ...base, local: clause.name.text, imported: "default", typeOnly: clause.isTypeOnly });
    }
    const named = clause.namedBindings;
    if (named !== undefined && ts.isNamespaceImport(named)) {
      found.push({ ...base, local: named.name.text, imported: "*", typeOnly: clause.isTypeOnly });
    } else if (named !== undefined) {
      for (const element of named.elements) {
        found.push({
          ...base, local: element.name.text, imported: (element.propertyName ?? element.name).text,
          typeOnly: clause.isTypeOnly || element.isTypeOnly,
        });
      }
    }
  }
  return found;
}

/**
 * Whether an import is of codeupipe itself: the package by its name, or the
 * index file of its source (the directory that has `payload.ts` and
 * `pipeline.ts`).
 */
export function isCoreImport(binding: ImportBinding): boolean {
  if (binding.specifier === "codeupipe" || binding.specifier.startsWith("codeupipe/")) return true;
  if (binding.file === undefined || !/^index\.[cm]?[jt]s$/.test(basename(binding.file))) return false;
  const directory = dirname(binding.file);
  return ["payload", "pipeline"].every((name) => isFile(join(directory, name + ".ts")) || isFile(join(directory, name + ".js")));
}

function hasModifier(node: ts.Node, kind: ts.SyntaxKind): boolean {
  return ts.canHaveModifiers(node) && (ts.getModifiers(node) ?? []).some((modifier) => modifier.kind === kind);
}

function topLevelClass(source: Source, name: string): ts.ClassDeclaration | undefined {
  return source.tree.statements.find(
    (statement): statement is ts.ClassDeclaration => ts.isClassDeclaration(statement) && statement.name?.text === name);
}

/**
 * The class that the name `name` means in the file `source`: a class of the
 * file, or a class that the file imports from a file of the project.
 */
export function findClass(source: Source, name: string, where: string): ClassRef {
  const own = topLevelClass(source, name);
  if (own !== undefined) return { source, node: own, name };

  const binding = importsOf(source).find((candidate) => candidate.local === name);
  if (binding === undefined) {
    throw new CompileRefusal(where, `\`${name}\` is not a class of ${basename(source.path)} and is not imported there`,
      "Declare the class at the top level of a file, and import it");
  }
  if (binding.file === undefined) {
    throw new CompileRefusal(where, `\`${name}\` comes from the package "${binding.specifier}", and its source is not read`,
      "Compile steps whose source is in the project");
  }
  const target = loadSource(binding.file);
  if (binding.imported === "default") {
    const node = target.tree.statements.find((statement): statement is ts.ClassDeclaration =>
      ts.isClassDeclaration(statement) && hasModifier(statement, ts.SyntaxKind.DefaultKeyword));
    if (node !== undefined) return { source: target, node, name: node.name?.text ?? name };
  } else if (binding.imported !== "*") {
    const node = topLevelClass(target, binding.imported);
    if (node !== undefined) return { source: target, node, name: binding.imported };
  }
  throw new CompileRefusal(where, `\`${name}\` is not a class at the top level of ${basename(binding.file)}`,
    "Declare the class in the file that it is imported from");
}

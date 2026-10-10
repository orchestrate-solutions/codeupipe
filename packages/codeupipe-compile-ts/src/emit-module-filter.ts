import { basename, dirname, relative, sep } from "node:path";

import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import { CompileRefusal } from "./compile-refusal.ts";
import { realPath } from "./real-path.ts";
import { importsOf, isCoreImport } from "./source-files.ts";
import type { ImportBinding } from "./source-files.ts";
import type { LoweredFunction, LoweredStep } from "./step-plan.ts";

const HELPERS: Record<string, string> = {
  cup_get: `function cup_get<T = unknown>(data: Map<string, unknown>, key: string): T | null;
function cup_get<T>(data: Map<string, unknown>, key: string, fallback: T): T;
function cup_get(data: Map<string, unknown>, key: string, fallback: unknown = null): unknown {
  return data.has(key) ? data.get(key) : fallback;
}`,
  cup_remove: `function cup_remove(data: Map<string, unknown>, key: string): Map<string, unknown> {
  data.delete(key);
  return data;
}`,
  cup_merge: `function cup_merge(data: Map<string, unknown>, other: Record<string, unknown>): Map<string, unknown> {
  for (const [key, value] of Object.entries(other)) data.set(key, value);
  return data;
}`,
};

/** The names that a file declares at its top level, without its imports. */
function topLevelNames(tree: ts.SourceFile): Set<string> {
  const names = new Set<string>();
  for (const statement of tree.statements) {
    if (ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) names.add(declaration.name.getText());
    } else if ((ts.isFunctionDeclaration(statement) || ts.isClassDeclaration(statement) || ts.isInterfaceDeclaration(statement)
      || ts.isTypeAliasDeclaration(statement) || ts.isEnumDeclaration(statement)) && statement.name !== undefined) {
      names.add(statement.name.text);
    }
  }
  return names;
}

/**
 * Writes the module: the imports that the steps need, the helpers, one
 * function for each step, and `run`.
 *
 * Input keys: `lowered`, `file`, `className`, optional `outFile` (the place
 * of the module, so that its imports are relative to it).
 * Output keys: `code`.
 */
export class EmitModuleFilter implements Filter {
  call(payload: Payload): Payload {
    const lowered = payload.get<LoweredStep[]>("lowered") ?? [];
    const outFile = payload.get<string>("outFile") ?? undefined;
    const functions: LoweredFunction[] = lowered.flatMap((step) =>
      step.kind === "filter" ? [step.filter] : step.kind === "tap" ? [step.tap] : [step.predicate, step.filter]);

    const imports = new Map<string, ImportBinding>();
    const helpers = new Set<string>();
    for (const lower of functions) {
      const bindings = importsOf(lower.source);
      const declared = topLevelNames(lower.source.tree);
      for (const name of lower.names) {
        if (HELPERS[name] !== undefined) {
          helpers.add(name);
          continue;
        }
        const binding = bindings.find((candidate) => candidate.local === name);
        if (binding !== undefined) {
          if (isCoreImport(binding)) {
            throw new CompileRefusal(lower.name, `the step uses \`${name}\` from codeupipe`,
              "Compiled code has no import of codeupipe. Use only the operations of the Payload");
          }
          const other = imports.get(name);
          if (other !== undefined && (other.imported !== binding.imported || (other.file ?? other.specifier) !== (binding.file ?? binding.specifier))) {
            throw new CompileRefusal(lower.name, `two steps import different things with the name \`${name}\``,
              "Give one of the imports another name");
          }
          imports.set(name, binding);
        } else if (declared.has(name)) {
          throw new CompileRefusal(lower.name, `the step uses \`${name}\`, which its file declares beside the class`,
            `Move \`${name}\` to its own file and import it`);
        }
      }
    }

    const specifierOf = (binding: ImportBinding): string => {
      if (binding.file === undefined) return binding.specifier;
      if (outFile === undefined) return binding.file;
      const path = relative(dirname(outFile), realPath(binding.file)).split(sep).join("/");
      return path.startsWith(".") ? path : "./" + path;
    };
    const importLines = [...imports.values()].sort((a, b) => (a.local < b.local ? -1 : 1)).map((binding) => {
      const type = binding.typeOnly ? "type " : "";
      const what = binding.imported === "default" ? binding.local
        : binding.imported === "*" ? `* as ${binding.local}`
        : binding.imported === binding.local ? `{ ${binding.local} }` : `{ ${binding.imported} as ${binding.local} }`;
      return `import ${type}${what} from ${JSON.stringify(specifierOf(binding))};`;
    });

    const invoke = (lower: LoweredFunction) => `${lower.isAsync ? "await " : ""}${lower.name}(data)`;
    const runLines = lowered.map((step) => {
      if (step.kind === "filter") return `  ${invoke(step.filter)};`;
      if (step.kind === "valve") return `  if (${step.predicate.name}(data)) ${invoke(step.filter)};`;
      // A Tap failure never stops the run.
      return `  try { ${invoke(step.tap)}; } catch { /* a Tap failure does not stop the run */ }`;
    });

    const file = payload.get<string>("file") ?? "";
    const parts = [
      `// Made by codeupipe-compile from ${basename(file)}:${payload.get<string>("className")}. Do not edit.\n`
      + "// This file has no import of codeupipe. It gives the same output as the pipeline.",
      ...(importLines.length > 0 ? [importLines.join("\n")] : []),
      ...[...helpers].sort().map((name) => HELPERS[name] ?? ""),
      ...functions.map((lower) => [...lower.consts, lower.code].join("\n")),
      "/** Runs the steps in order on a copy of `input`, and returns the result. */\n"
      + "export async function run(input: Record<string, unknown>): Promise<Record<string, unknown>> {\n"
      + "  const data = new Map<string, unknown>(Object.entries(input));\n"
      + (runLines.length > 0 ? runLines.join("\n") + "\n" : "")
      + "  return Object.fromEntries(data);\n}",
    ];
    return payload.insert("code", parts.join("\n\n") + "\n");
  }
}

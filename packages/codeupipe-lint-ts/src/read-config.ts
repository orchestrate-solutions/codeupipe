import { existsSync, readFileSync } from "node:fs";

export const CONFIG_NAME = "cup.config.json";
const LINT_KEYS = ["paths", "exclude", "disable"];

export type LintConfig = { paths?: string[]; exclude?: string[]; disable?: string[] };

/**
 * The `lint` section of the config file, checked. Undefined when the file
 * is not there. With `path` given, a file that is not there is an error.
 *
 * A key that the linter does not read is an error, so the file cannot hold a
 * setting that does nothing. Other sections of the file are for other tools.
 */
export function readLintConfig(path?: string): LintConfig | undefined {
  const name = path ?? CONFIG_NAME;
  if (!existsSync(name)) {
    if (path === undefined) return undefined;
    throw new Error(`${name}: no such file`);
  }
  let config: unknown;
  try {
    config = JSON.parse(readFileSync(name, "utf8"));
  } catch (error) {
    throw new Error(`${name} is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
  if (typeof config !== "object" || config === null || Array.isArray(config)) {
    throw new Error(`${name} must hold a JSON object`);
  }
  const lint = (config as Record<string, unknown>).lint ?? {};
  if (typeof lint !== "object" || lint === null || Array.isArray(lint)) {
    throw new Error(`${name}: lint must be an object`);
  }
  for (const [key, value] of Object.entries(lint)) {
    if (!LINT_KEYS.includes(key)) {
      throw new Error(`${name}: lint: unknown key '${key}' (the keys are ${LINT_KEYS.join(", ")})`);
    }
    if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
      throw new Error(`${name}: lint.${key} must be a list of strings`);
    }
  }
  return lint as LintConfig;
}

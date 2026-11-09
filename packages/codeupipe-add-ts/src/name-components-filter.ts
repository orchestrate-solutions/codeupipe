// NameComponentsFilter: the type name and the paths of each component, as in phase 1.
import { Payload } from "codeupipe";
import type { Filter } from "codeupipe";

import { Refusal } from "./add-refusal.ts";
import type { LaidOut } from "./check-layout-filter.ts";
import { PlanFilesFilter } from "./plan-files-filter.ts";
import { TypeNameFilter } from "./type-name-filter.ts";

/** A component of the layout, with the names and the paths of phase 1. */
export type Named = LaidOut & {
  type_name: string;
  kebab: string;
  component_path: string;
  test_path: string;
  import_path: string;
};

const KEYS = ["type_name", "kebab", "component_path", "test_path", "import_path"] as const;

/**
 * Filter (sync).
 *
 * Input keys: `components`, `directory`.
 * Output keys: `components`, each with `type_name`, `kebab`,
 * `component_path`, `test_path` and `import_path` added. It uses the Filters
 * of phase 1, so the names are the same. A name that phase 1 refuses, or two
 * components with the same type name, are refused with exit code 2.
 */
export class NameComponentsFilter implements Filter {
  call(payload: Payload): Payload {
    const seen = new Map<string, string>();
    const named = payload.get<LaidOut[]>("components", []).map((component): Named => {
      let one = new Payload({ kind: component.kind, name: component.name, directory: payload.get<string>("directory") });
      one = new PlanFilesFilter().call(new TypeNameFilter().call(one));
      const typeName = one.get<string>("type_name", "");
      if (seen.has(typeName)) {
        throw new Refusal(2, `Two components are ${typeName}: ${seen.get(typeName)} and ${component.name}.`);
      }
      seen.set(typeName, component.name);
      const names = Object.fromEntries(KEYS.map((key) => [key, one.get<string>(key, "")]));
      return { ...component, ...names } as Named;
    });
    return payload.insert("components", named);
  }
}

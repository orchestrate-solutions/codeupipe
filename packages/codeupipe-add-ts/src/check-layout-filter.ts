// CheckLayoutFilter: the keys of the layout, and the shape of each (ADD.md, "The keys").
import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";

export const LANG = "typescript";
export const LAYOUT_KEYS = ["lang", "root", "components"];
export const COMPONENT_KEYS = ["kind", "name", "description", "steps", "hooks"];

/** A step of a pipeline: a name, or `valve: [Predicate, Filter]`. */
export type Step = string | { valve: [string, string] };

/** A component of the layout, with each key of COMPONENT_KEYS. */
export type LaidOut = { kind: string; name: string; description: string; steps: Step[]; hooks: string[] };

type Mapping = Record<string, unknown>;

/**
 * Filter (sync).
 *
 * Input keys: `layout`.
 * Output keys: `directory` (`root`, or `.`), and `components`: each with
 * every key of COMPONENT_KEYS. A key that is not known, a key that is
 * missing, or a value of the wrong shape is refused with exit code 2. The
 * names are checked by the next steps.
 */
export class CheckLayoutFilter implements Filter {
  call(payload: Payload): Payload {
    const layout = payload.get<Mapping>("layout", {});
    this.known(layout, LAYOUT_KEYS, "the layout");
    if (!("lang" in layout)) throw new Refusal(2, `The layout has no lang:. For this command it is lang: ${LANG}.`);
    if (layout["lang"] !== LANG) {
      throw new Refusal(2, `The layout is for ${String(layout["lang"])}, and this is codeupipe add for ${LANG}.`);
    }
    const root = layout["root"] ?? ".";
    if (typeof root !== "string" || root === "") throw new Refusal(2, "root: is a directory, such as src/pricing.");
    const listed = layout["components"];
    if (!Array.isArray(listed) || listed.length === 0) {
      throw new Refusal(2, "components: is a list with one component or more, each with kind: and name:.");
    }
    return payload.insert("directory", root).insert("components", listed.map((item) => this.component(item)));
  }

  private isMapping(value: unknown): value is Mapping {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }

  private isStep(step: unknown): step is Step {
    if (typeof step === "string") return true;
    if (!this.isMapping(step) || Object.keys(step).join() !== "valve") return false;
    const pair = step["valve"];
    return Array.isArray(pair) && pair.length === 2 && pair.every((name) => typeof name === "string");
  }

  private show(value: unknown): string {
    return JSON.stringify(value) ?? String(value);
  }

  private known(mapping: Mapping, keys: string[], label: string): void {
    const unknown = Object.keys(mapping).filter((key) => !keys.includes(key));
    if (unknown.length > 0) {
      throw new Refusal(2, `Unknown key ${unknown.join(", ")} in ${label}. The keys are: ${keys.join(", ")}.`);
    }
  }

  private component(item: unknown): LaidOut {
    if (!this.isMapping(item)) throw new Refusal(2, `A component is a mapping with kind: and name:, not ${this.show(item)}.`);
    const label = `the component ${typeof item["name"] === "string" ? item["name"] : "with no name"}`;
    this.known(item, COMPONENT_KEYS, label);
    for (const key of ["kind", "name"]) {
      if (typeof item[key] !== "string") throw new Refusal(2, `${label[0]?.toUpperCase()}${label.slice(1)} has no ${key}:.`);
    }
    const kind = item["kind"] as string;
    const name = item["name"] as string;
    const description = item["description"] ?? "";
    if (typeof description !== "string") throw new Refusal(2, `The description of ${label} is not a text.`);
    for (const key of ["steps", "hooks"]) {
      if (key in item && kind !== "pipeline") {
        throw new Refusal(2, `${key}: is only for a pipeline, and ${name} is a ${kind}.`);
      }
    }
    const steps = item["steps"] ?? [];
    const hooks = item["hooks"] ?? [];
    if (!Array.isArray(steps)) {
      throw new Refusal(2, `The steps of ${name} are a list. A step is a name, or valve: [Predicate, Filter].`);
    }
    for (const step of steps) {
      if (!this.isStep(step)) {
        throw new Refusal(2, `The step ${this.show(step)} of ${name} cannot be read. A step is a name, or valve: [Predicate, Filter].`);
      }
    }
    if (!Array.isArray(hooks) || !hooks.every((hook) => typeof hook === "string")) {
      throw new Refusal(2, `The hooks of ${name} are a list of names.`);
    }
    return { kind, name, description, steps: steps as Step[], hooks: hooks as string[] };
  }
}

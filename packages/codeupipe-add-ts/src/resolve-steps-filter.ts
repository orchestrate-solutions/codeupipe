// ResolveStepsFilter: the calls and the imports of each pipeline of the layout (ADD.md, "The steps").
import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";
import type { Named } from "./name-components-filter.ts";

/** The call that each kind of step gives. */
export const CALLS: Record<string, string> = { filter: "addFilter", tap: "addTap", pipeline: "addPipeline" };

/** A call of a pipeline: the method, and the type names in it. */
export type Call = [string, string[]];

/** A component, with its calls (steps first, then hooks) and its imports, as `[kebab, type name]`. */
export type Resolved = Named & { calls: Call[]; imports: Array<[string, string]> };

/**
 * Filter (sync).
 *
 * Input keys: `components`, each with `kind`, `name`, `type_name`, `kebab`,
 * `steps` and `hooks`.
 * Output keys: `components`, each with `calls` and `imports`. A name that is
 * not a component, a step of the wrong kind, or a pipeline that has itself as
 * a step is refused with exit code 2.
 */
export class ResolveStepsFilter implements Filter {
  call(payload: Payload): Payload {
    const components = payload.get<Named[]>("components", []);
    const found = new Map<string, Named>();
    for (const component of components) found.set(component.name, component).set(component.type_name, component);
    const resolved = components.map((component) => this.resolve(component, found));
    const byType = new Map(resolved.map((component) => [component.type_name, component]));
    for (const component of resolved) this.refuseALoop(component, byType, []);
    return payload.insert("components", resolved);
  }

  private find(name: string, found: Map<string, Named>, component: Named): Named {
    const used = found.get(name);
    if (used === undefined) throw new Refusal(2, `${name}, a step of ${component.name}, is not a component of the layout.`);
    return used;
  }

  private resolve(component: Named, found: Map<string, Named>): Resolved {
    const calls: Array<[string, Named[]]> = [];
    for (const step of component.steps) {
      if (typeof step !== "string") {
        const pair = step.valve.map((name) => this.find(name, found, component));
        pair.forEach((used, at) => {
          const wanted = at === 0 ? "predicate" : "filter";
          if (used.kind !== wanted) {
            throw new Refusal(2, `valve: [${step.valve.join(", ")}] in ${component.name}: a valve is [Predicate, Filter], `
              + `and ${used.name} is a ${used.kind}, not a ${wanted}.`);
          }
        });
        calls.push(["addValve", pair]);
        continue;
      }
      const used = this.find(step, found, component);
      if (used.kind === "predicate") {
        throw new Refusal(2, `${used.name} is a predicate. A predicate is not a step: put it in a valve: [${used.name}, Filter].`);
      }
      if (used.kind === "hook") {
        throw new Refusal(2, `${used.name} is a hook. A hook is not a step: put it in hooks: of ${component.name}.`);
      }
      calls.push([CALLS[used.kind] ?? "", [used]]);
    }
    for (const name of component.hooks) {
      const hook = this.find(name, found, component);
      if (hook.kind !== "hook") throw new Refusal(2, `${name} in the hooks of ${component.name} is a ${hook.kind}, not a hook.`);
      calls.push(["useHook", [hook]]);
    }
    const imports = new Map<string, [string, string]>();
    for (const [, usedList] of calls) {
      for (const used of usedList) imports.set(used.kebab, [used.kebab, used.type_name]);
    }
    return {
      ...component,
      calls: calls.map(([method, usedList]): Call => [method, usedList.map((used) => used.type_name)]),
      imports: [...imports.values()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)),
    };
  }

  private refuseALoop(component: Resolved, byType: Map<string, Resolved>, path: string[]): void {
    if (path.includes(component.type_name)) {
      const loop = [...path.slice(path.indexOf(component.type_name)), component.type_name];
      throw new Refusal(2, `A pipeline has itself as a step: ${loop.join(" -> ")}.`);
    }
    for (const [method, names] of component.calls) {
      const nested = byType.get(names[0] ?? "");
      if (method === "addPipeline" && nested) this.refuseALoop(nested, byType, [...path, component.type_name]);
    }
  }
}

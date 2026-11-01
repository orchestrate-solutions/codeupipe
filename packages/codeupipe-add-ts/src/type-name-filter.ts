// TypeNameFilter: the type name and the file name, from the kind and the name (ADD.md, "Names").
import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";

/** The role that each kind adds to the name. */
export const ROLES: Record<string, string> = {
  filter: "Filter",
  predicate: "Predicate",
  tap: "Tap",
  hook: "Hook",
  pipeline: "Pipeline",
};

/** The kinds that a user does not write, each with the reason that the contract gives. */
const NOT_MADE: Record<string, string> = {
  valve: "A Valve is not a type. Make a Predicate and a Filter, and join them with add_valve(predicate, filter).",
  payload: "The runtime makes the Payload. A user does not write one.",
  state: "The runtime makes the State. A user does not write one.",
};

const NAME = /^[A-Za-z][A-Za-z0-9_-]*$/;

/** The rule of the linters (CUP-I006): where a word starts in a type name. */
const WORD_BREAK = /(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g;

/**
 * Filter (sync).
 *
 * Input keys: `kind`, `name`.
 * Output keys: `type_name` (`DiscountFilter`) and `kebab`
 * (`discount-filter`). A kind or a name that cannot be used is refused with
 * exit code 2.
 */
export class TypeNameFilter implements Filter {
  call(payload: Payload): Payload {
    const kind: string = payload.get<string>("kind", "");
    const name: string = payload.get<string>("name", "");
    if (NOT_MADE[kind] !== undefined) throw new Refusal(2, NOT_MADE[kind]);
    if (ROLES[kind] === undefined) {
      throw new Refusal(2, `Unknown kind '${kind}'. The kinds are: filter, predicate, tap, hook, pipeline.`);
    }
    if (name === "" || name === undefined || !NAME.test(name)) {
      throw new Refusal(2, `The name '${name}' cannot be used. The name starts with a letter, and has only `
        + "letters, digits, _ and -.");
    }
    const role = ROLES[kind] ?? "";
    const pascal = name.split(/[_-]+/).filter((word) => word !== "")
      .map((word) => word.slice(0, 1).toUpperCase() + word.slice(1)).join("");
    const typeName = pascal.endsWith(role) ? pascal : pascal + role;
    return payload.insert("type_name", typeName).insert("kebab", typeName.replace(WORD_BREAK, "-").toLowerCase());
  }
}

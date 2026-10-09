/**
 * Predicate: a Valve's condition (conformance/API.md, "Valve").
 *
 * An object with `test(payload) -> boolean`, identified by its class (the
 * build step's stamp) like a step, with any configuration on the instance:
 *
 *     class AtLeast implements Predicate {
 *       constructor(private readonly n: number) {}
 *       test(p: Payload) { return (p.get("n", 0) as number) >= this.n; }
 *     }
 *
 * Functions, arrows and object literals are not predicates.
 */

import type { Payload, PayloadData } from "./payload.js";

export interface Predicate<T extends PayloadData = PayloadData> {
  test(payload: Payload<T>): boolean;
}

import type { Filter } from "./filter.ts";
import type { Predicate } from "./predicate.ts";

/**
 * Valve: joins a Predicate to a Filter. The Filter runs only when the
 * Predicate is true.
 *
 * `Pipeline.addValve(predicate, filter)` makes one. It is not a public name.
 */
export class Valve {
  readonly predicate: Predicate;
  readonly filter: Filter;

  constructor(predicate: Predicate, filter: Filter) {
    this.predicate = predicate;
    this.filter = filter;
  }
}

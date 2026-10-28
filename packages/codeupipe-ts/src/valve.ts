import type { Filter } from "./filter.ts";
import type { Predicate } from "./predicate.ts";

/**
 * Valve: joins a Predicate to a Filter. The Filter runs only when the
 * Predicate is true.
 *
 * `Pipeline.addValve(predicate, filter)` makes one. It is not a public name.
 */
export class Valve<P> {
  readonly predicate: Predicate<P>;
  readonly filter: Filter<P>;

  constructor(predicate: Predicate<P>, filter: Filter<P>) {
    this.predicate = predicate;
    this.filter = filter;
  }
}

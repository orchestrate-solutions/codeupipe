import type { Payload, Predicate } from "../../src/index.ts";

/**
 * A Predicate: the question that a Valve asks. Its settings are on the
 * instance, so the same class answers a different question in another
 * pipeline.
 */
export class AtLeastPredicate implements Predicate {
  readonly key: string;
  readonly minimum: number;

  constructor(key: string, minimum: number) {
    this.key = key;
    this.minimum = minimum;
  }

  test(payload: Payload): boolean {
    return payload.get(this.key, 0) >= this.minimum;
  }
}

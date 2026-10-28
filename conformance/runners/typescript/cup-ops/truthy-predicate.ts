import type { Payload, Predicate } from "../../../../packages/codeupipe-ts/src/index.ts";

/** get(key) is truthy; a missing key is false */
export class TruthyPredicate implements Predicate {
  readonly key: string;

  constructor(key: string) {
    this.key = key;
  }

  test(payload: Payload): boolean {
    return Boolean(payload.get(this.key));
  }
}

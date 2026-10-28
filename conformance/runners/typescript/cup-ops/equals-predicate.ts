import type { Payload, Predicate } from "../../../../packages/codeupipe-ts/src/index.ts";

/** get(key) == value */
export class EqualsPredicate implements Predicate {
  readonly key: string;
  readonly value: unknown;

  constructor(key: string, value: unknown) {
    this.key = key;
    this.value = value;
  }

  test(payload: Payload): boolean {
    return payload.get(this.key) === this.value;
  }
}

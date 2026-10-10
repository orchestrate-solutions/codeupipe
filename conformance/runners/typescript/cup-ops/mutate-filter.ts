import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** insert(key, value) as a statement of its own, then return the payload */
export class MutateFilter implements Filter {
  readonly key: string;
  readonly value: unknown;

  constructor(key: string, value: unknown) {
    this.key = key;
    this.value = value;
  }

  call(payload: Payload): Payload {
    payload.insert(this.key, this.value);
    return payload;
  }
}

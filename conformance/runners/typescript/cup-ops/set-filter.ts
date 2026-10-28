import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** insert key = value */
export class SetFilter implements Filter {
  readonly key: string;
  readonly value: unknown;

  constructor(key: string, value: unknown) {
    this.key = key;
    this.value = value;
  }

  call(payload: Payload): Payload {
    return payload.insert(this.key, this.value);
  }
}

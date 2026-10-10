import { Payload } from "../../../../packages/codeupipe-ts/src/index.ts";
import type { Filter } from "../../../../packages/codeupipe-ts/src/index.ts";

/** merge(Payload(value)) */
export class MergeFilter implements Filter {
  readonly value: Record<string, unknown>;

  constructor(value: Record<string, unknown>) {
    this.value = value;
  }

  call(payload: Payload): Payload {
    return payload.merge(new Payload(this.value));
  }
}

import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** remove(key) */
export class RemoveFilter implements Filter {
  readonly key: string;

  constructor(key: string) {
    this.key = key;
  }

  call(payload: Payload): Payload {
    return payload.remove(this.key);
  }
}

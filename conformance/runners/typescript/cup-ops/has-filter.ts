import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** insert to = has(key) */
export class HasFilter implements Filter {
  readonly key: string;
  readonly to: string;

  constructor(key: string, to: string) {
    this.key = key;
    this.to = to;
  }

  call(payload: Payload): Payload {
    return payload.insert(this.to, payload.has(this.key));
  }
}

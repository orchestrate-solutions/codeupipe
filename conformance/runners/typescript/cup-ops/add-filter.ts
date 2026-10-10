import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** insert key = get(key, 0) + by */
export class AddFilter implements Filter {
  readonly key: string;
  readonly by: number;

  constructor(key: string, by: number) {
    this.key = key;
    this.by = by;
  }

  call(payload: Payload): Payload {
    return payload.insert(this.key, payload.get(this.key, 0) + this.by);
  }
}

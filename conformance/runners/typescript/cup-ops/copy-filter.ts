import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** insert to = get(from), null if missing */
export class CopyFilter implements Filter {
  readonly from: string;
  readonly to: string;

  constructor(from: string, to: string) {
    this.from = from;
    this.to = to;
  }

  call(payload: Payload): Payload {
    return payload.insert(this.to, payload.get(this.from));
  }
}

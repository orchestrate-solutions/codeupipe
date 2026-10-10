import type { Filter, Payload } from "../../src/index.ts";

/** A Filter. */
export class MarkBulkFilter implements Filter {
  call(payload: Payload): Payload {
    return payload.insert("bulk", true);
  }
}

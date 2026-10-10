import type { Payload, Tap } from "../../../../packages/codeupipe-ts/src/index.ts";
import { TAPS } from "./sink.ts";

/** append get(key) to the runner's tap log */
export class RecordTap implements Tap {
  readonly key: string;

  constructor(key: string) {
    this.key = key;
  }

  observe(payload: Payload): void {
    TAPS.push(payload.get(this.key));
  }
}

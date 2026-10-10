import type { Payload, Tap } from "../../../../packages/codeupipe-ts/src/index.ts";

/** append get(key) to the runner's tap log */
export class RecordTap implements Tap {
  readonly key: string;
  readonly log: unknown[];

  constructor(key: string, log: unknown[]) {
    this.key = key;
    this.log = log;
  }

  observe(payload: Payload): void {
    this.log.push(payload.get(this.key));
  }
}

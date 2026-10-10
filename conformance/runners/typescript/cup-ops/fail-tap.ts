import type { Payload, Tap } from "../../../../packages/codeupipe-ts/src/index.ts";

/** throw */
export class FailTap implements Tap {
  readonly message: string;

  constructor(message: string) {
    this.message = message;
  }

  observe(_payload: Payload): void {
    throw new Error(this.message);
  }
}

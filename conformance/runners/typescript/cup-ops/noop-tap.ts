import type { Payload, Tap } from "../../../../packages/codeupipe-ts/src/index.ts";

/** do nothing */
export class NoopTap implements Tap {
  observe(_payload: Payload): void {}
}

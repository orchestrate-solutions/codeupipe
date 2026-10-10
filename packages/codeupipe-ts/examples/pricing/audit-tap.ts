import type { Payload, Tap } from "../../src/index.ts";

/**
 * A Tap: reads the Payload and returns nothing. This one fails every time,
 * to show that a Tap failure is recorded and never stops the run.
 */
export class AuditTap implements Tap {
  observe(_payload: Payload): void {
    throw new Error("audit sink is down");
  }
}

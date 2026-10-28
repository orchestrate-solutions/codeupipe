import type { Payload, Tap } from "../../src/index.ts";

/**
 * A Tap: reads the Payload and returns nothing. If it fails, State records
 * the error and the run goes on.
 */
export class AuditTap implements Tap {
  observe(payload: Payload): void {
    console.log("audit:", payload.toDict());
  }
}

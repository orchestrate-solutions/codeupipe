import { Hook } from "../../../../packages/codeupipe-ts/src/index.ts";

/**
 * Records before:<step>, after:<step> and error:<step>. Events of the
 * pipeline itself have an empty step.
 */
export class RecordHook extends Hook {
  readonly events: string[];

  constructor(events: string[]) {
    super();
    this.events = events;
  }

  override before(step: string | null): void {
    this.events.push("before:" + (step ?? ""));
  }

  override after(step: string | null): void {
    this.events.push("after:" + (step ?? ""));
  }

  override onError(step: string | null): void {
    this.events.push("error:" + (step ?? ""));
  }
}

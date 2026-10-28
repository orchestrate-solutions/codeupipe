import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

import { RUN_AGAIN } from "./sink.ts";

/**
 * The reference `run_again` step (conformance/README.md): it starts a second
 * run of the pipeline that it is in, inside the first one. How a pipeline is
 * run again depends on the target, so the runner gives that as a function,
 * in `RUN_AGAIN`. The second run has `inner` in its input, so it does not
 * start a third one.
 */
export class RunAgainFilter implements Filter {
  readonly data: Record<string, unknown>;

  constructor(data: Record<string, unknown>) {
    this.data = data;
  }

  async call(payload: Payload): Promise<Payload> {
    if (payload.get("inner") !== true) {
      await RUN_AGAIN.run({ ...this.data });
    }
    return payload;
  }
}

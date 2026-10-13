import { Payload, State } from "../../../../packages/codeupipe-ts/src/index.ts";
import type { Filter, Pipeline } from "../../../../packages/codeupipe-ts/src/index.ts";

import { INNER_STATES } from "./sink.ts";

/**
 * The reference `run_again` step (conformance/README.md): it starts a second
 * run of the pipeline that it is in, inside the first one. The runner sets
 * `pipeline` after it builds the pipeline. The second run has `inner` in its
 * input, so it does not start a third one.
 */
export class RunAgainFilter implements Filter {
  readonly data: Record<string, unknown>;
  pipeline: Pipeline | null = null;

  constructor(data: Record<string, unknown>) {
    this.data = data;
  }

  async call(payload: Payload): Promise<Payload> {
    if (payload.get("inner") !== true && this.pipeline !== null) {
      const state = new State();
      INNER_STATES.push(state);
      await this.pipeline.run(new Payload({ ...this.data }), state);
    }
    return payload;
  }
}

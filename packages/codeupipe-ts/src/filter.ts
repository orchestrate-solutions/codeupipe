import type { Payload } from "./payload.ts";

/** Filter: changes the data. A failure throws. `call` can be async. */
export interface Filter<P = Payload> {
  call(payload: P): P | Promise<P>;
}

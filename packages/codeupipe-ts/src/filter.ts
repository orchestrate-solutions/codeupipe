import type { Payload } from "./payload.ts";

/** Filter: changes the data. A failure throws. `call` can be async. */
export interface Filter {
  call(payload: Payload): Payload | Promise<Payload>;
}

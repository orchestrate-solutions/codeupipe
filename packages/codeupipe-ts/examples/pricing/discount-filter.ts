import type { Filter, Payload } from "../../src/index.ts";

/** A Filter: takes the Payload, writes to it, returns it. */
export class DiscountFilter implements Filter {
  readonly rate: number;

  constructor(rate: number) {
    this.rate = rate;
  }

  call(payload: Payload): Payload {
    const price = payload.get("price", 0) * (1 - this.rate);
    return payload.insert("price", Math.round(price * 100) / 100);
  }
}

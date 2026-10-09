import { describe, it, expect } from "vitest";
import { Payload } from "../src/payload.js";
import { Valve } from "../src/valve.js";
import type { Filter } from "../src/filter.js";
import type { Predicate } from "../src/predicate.js";

class DoubleX implements Filter {
  async call(payload: Payload): Promise<Payload> {
    const x = payload.get("x") as number;
    return payload.insert("x", x * 2);
  }
}

class IsPositive implements Predicate {
  test(p: Payload): boolean {
    return (p.get("x") as number) > 0;
  }
}

class Always implements Predicate {
  test(): boolean {
    return true;
  }
}

describe("Valve", () => {
  it("executes when predicate is true", async () => {
    const valve = new Valve(new DoubleX(), new IsPositive());
    const result = await valve.call(new Payload({ x: 5 }));
    expect(result.get("x")).toBe(10);
    expect(valve._lastSkipped).toBe(false);
  });

  it("skips when predicate is false", async () => {
    const valve = new Valve(new DoubleX(), new IsPositive());
    const result = await valve.call(new Payload({ x: -1 }));
    expect(result.get("x")).toBe(-1); // unchanged
    expect(valve._lastSkipped).toBe(true);
  });

  it("toString names the inner filter and the predicate", () => {
    const valve = new Valve(new DoubleX(), new Always());
    expect(valve.toString()).toContain("DoubleX");
    expect(valve.toString()).toContain("valve.test#Always");
  });

  it("conforms to Filter interface (can be used in pipeline)", async () => {
    const valve: Filter = new Valve(new DoubleX(), new Always());
    const result = await valve.call(new Payload({ x: 3 }));
    expect(result.get("x")).toBe(6);
  });
});

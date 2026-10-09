/**
 * TypedPipeline<Ctx> — orchestrator for typed payloads.
 *
 * Same shape as Pipeline: filters, taps, valves, hooks, and State.
 * Ctx flows through unchanged in type; its data mutates according to
 * your filter implementations.
 *
 * Manifesto invariants preserved:
 * 1. Removing every Tap yields identical output.
 * 2. Same ctx through same pipeline yields same output.
 */

import { State } from "../state.js";
import type { TypedFilter } from "./filter.js";
import type { TypedHook } from "./hook.js";
import type { TypedTap } from "./tap.js";

type Kind = "filter" | "tap";
type StepEntry<Ctx> = {
  name: string;
  step: TypedFilter<Ctx> | TypedTap<Ctx>;
  kind: Kind;
};

export class TypedPipeline<Ctx> {
  private readonly steps: StepEntry<Ctx>[] = [];
  private readonly hooks: TypedHook<Ctx>[] = [];
  private _state: State = new State();
  private _observeTiming = false;
  private _observeState = true;
  private readonly disabledTaps = new Set<string>();

  addFilter(filter: TypedFilter<Ctx>, name?: string): this {
    this.steps.push({
      name: name ?? filter.name ?? filter.constructor.name,
      step: filter,
      kind: "filter",
    });
    return this;
  }

  addTap(tap: TypedTap<Ctx>, name?: string): this {
    this.steps.push({
      name: name ?? tap.name ?? tap.constructor.name,
      step: tap,
      kind: "tap",
    });
    return this;
  }

  useHook(hook: TypedHook<Ctx>): this {
    this.hooks.push(hook);
    return this;
  }

  observe(timing = false): this {
    this._observeTiming = timing;
    return this;
  }

  observeState(enabled: boolean): this {
    this._observeState = enabled;
    return this;
  }

  disableTaps(...names: string[]): this {
    for (const n of names) this.disabledTaps.add(n);
    return this;
  }

  get state(): State {
    return this._state;
  }

  stepCount(): number {
    return this.steps.length;
  }

  describe(): Array<[string, Kind]> {
    return this.steps.map((s) => [s.name, s.kind]);
  }

  private canRunFast(): boolean {
    return (
      this.hooks.length === 0 &&
      !this._observeTiming &&
      this.disabledTaps.size === 0 &&
      this.steps.every((s) => s.kind === "filter")
    );
  }

  private async runFast(ctx: Ctx): Promise<Ctx> {
    this._state = new State();
    const observeState = this._observeState;
    for (const { name, step } of this.steps) {
      ctx = await (step as TypedFilter<Ctx>).call(ctx);
      if (observeState) {
        const s = step as { lastSkipped?: boolean; _lastSkipped?: boolean };
        const skipped = s.lastSkipped === true || s._lastSkipped === true;
        if (skipped) this._state.markSkipped(name);
        else this._state.markExecuted(name);
      }
    }
    return ctx;
  }

  async run(initial: Ctx): Promise<Ctx> {
    if (this.canRunFast()) return this.runFast(initial);

    this._state = new State();
    let ctx = initial;

    for (const hook of this.hooks) await hook.before?.(undefined, ctx);

    for (const { name, step, kind } of this.steps) {
      const t0 = this._observeTiming ? performance.now() : 0;

      if (kind === "tap") {
        if (this.disabledTaps.has(name)) {
          if (this._observeState) this._state.markSkipped(name);
          continue;
        }
        try {
          await (step as TypedTap<Ctx>).observe(ctx);
        } catch {
          /* taps swallow — manifesto invariant */
        }
        if (this._observeState) this._state.markExecuted(name);
        continue;
      }

      for (const hook of this.hooks) await hook.before?.(name, ctx);

      try {
        ctx = await (step as TypedFilter<Ctx>).call(ctx);
      } catch (e) {
        const err = e instanceof Error ? e : new Error(String(e));
        for (const hook of this.hooks) await hook.onError?.(name, err);
        throw e;
      }

      if (this._observeState) {
        const s = step as { lastSkipped?: boolean; _lastSkipped?: boolean };
        const skipped = s.lastSkipped === true || s._lastSkipped === true;
        if (skipped) this._state.markSkipped(name);
        else this._state.markExecuted(name);
      }

      for (const hook of this.hooks) await hook.after?.(name, ctx);

      if (this._observeTiming) {
        this._state.recordTiming(name, (performance.now() - t0) / 1000);
      }
    }

    for (const hook of this.hooks) await hook.after?.(undefined, ctx);
    return ctx;
  }
}

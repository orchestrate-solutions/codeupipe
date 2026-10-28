import type { Filter } from "./filter.ts";
import type { Hook } from "./hook.ts";
import type { Payload } from "./payload.ts";
import type { PipelineData } from "./pipeline-data.ts";
import type { Predicate } from "./predicate.ts";
import { State } from "./state.ts";
import { labelOf } from "./step-label.ts";
import type { Tap } from "./tap.ts";
import { Valve } from "./valve.ts";

type Step<P extends PipelineData<P>> =
  | { kind: "filter"; label: string; filter: Filter<P> }
  | { kind: "valve"; label: string; valve: Valve<P> }
  | { kind: "tap"; label: string; tap: Tap<P> }
  | { kind: "pipeline"; label: string; pipeline: Pipeline<P> };

// The clock of browsers and of Node. Declared here so that this file needs
// the types of neither.
declare const performance: { now(): number };

function isThenable(value: unknown): value is PromiseLike<unknown> {
  return typeof (value as { then?: unknown } | null | undefined)?.then === "function";
}

/** Whether `value` is an object with `method`. A function is not a step: every function has `call`. */
function has(value: unknown, method: string): boolean {
  return typeof value === "object" && value !== null
    && typeof (value as Record<string, unknown>)[method] === "function";
}

/** Refuse a step that does not have the method of its role. */
function require(step: unknown, method: string, what: string): void { // cup: allow-plain the framework itself: a primitive is made of this
  if (!has(step, method)) {
    const given = step === null || step === undefined ? String(step)
      : typeof step === "function" ? "a function" : `a ${labelOf(step)}`;
    throw new TypeError(`${what} has ${method}(payload). The value that was given (${given}) does not.`);
  }
}

/**
 * Pipeline: runs the steps in order.
 *
 * Filters change the Payload, Valves gate a Filter, Taps read, Hooks see the
 * lifecycle, and State records what ran. Add steps with `addFilter`,
 * `addValve`, `addTap` and `addPipeline`, add Hooks with `useHook`, and run
 * with `await pipeline.run(payload)`.
 *
 * It carries a Payload unless you give it a type of your own
 * (`new Pipeline<Order>()`, see `PipelineData`).
 */
export class Pipeline<P extends PipelineData<P> = Payload> {
  #steps: Step<P>[] = [];
  #uses: Map<string, number> = new Map();
  #hooks: Hook<P>[] = [];
  #state: State = new State();
  #timing = false;
  #lineage = false;

  /** What happened in the run that started last. */
  get state(): State {
    return this.#state;
  }

  /** The label of each step, in order. */
  get labels(): string[] {
    return this.#steps.map((step) => step.label);
  }

  /** The class name of the step, with a number from its second use in this pipeline. */
  #label(step: unknown): string {
    const base = labelOf(step);
    const count = (this.#uses.get(base) ?? 0) + 1;
    this.#uses.set(base, count);
    return count === 1 ? base : `${base}#${count}`;
  }

  /** Add a Filter. */
  addFilter(filter: Filter<P>): void {
    require(filter, "call", "A Filter");
    this.#steps.push({ kind: "filter", label: this.#label(filter), filter });
  }

  /**
   * Add a Valve: `filter` runs only when `predicate.test(payload)` is true.
   *
   * The condition comes first, then the Filter that it controls. When the
   * test is false the Payload passes through unchanged and the step is
   * recorded as skipped. The step has the label of its Filter.
   */
  addValve(predicate: Predicate<P>, filter: Filter<P>): void {
    if (!has(predicate, "test") && has(predicate, "call") && has(filter, "test")) {
      throw new TypeError("The arguments are in the wrong order: addValve(predicate, filter). "
        + "The condition comes first, then the Filter.");
    }
    require(predicate, "test", "A Predicate");
    require(filter, "call", "A Filter");
    this.#steps.push({ kind: "valve", label: this.#label(filter), valve: new Valve(predicate, filter) });
  }

  /** Add a Tap. */
  addTap(tap: Tap<P>): void {
    require(tap, "observe", "A Tap");
    this.#steps.push({ kind: "tap", label: this.#label(tap), tap });
  }

  /** Nest a Pipeline as one step of this Pipeline. */
  addPipeline(pipeline: Pipeline<P>): void {
    if (!(pipeline instanceof Pipeline)) {
      throw new TypeError("addPipeline takes a Pipeline. The value that was given is not one.");
    }
    this.#steps.push({ kind: "pipeline", label: this.#label(pipeline), pipeline });
  }

  /** Add a Hook. */
  useHook(hook: Hook<P>): void {
    this.#hooks.push(hook);
  }

  /**
   * Turn on timing (seconds for each step, in State) and lineage (labels on
   * the Payload). A type of your own keeps lineage only if it has `_stamp`.
   */
  observe(options: { timing?: boolean; lineage?: boolean } = {}): void {
    this.#timing = options.timing ?? true;
    this.#lineage = options.lineage ?? false;
  }

  /**
   * Run the steps in order on a copy of `initial`, and return the result.
   *
   * A step can be sync or async. A Filter failure stops the run and is
   * thrown again after the Hooks have seen it. A Tap failure is recorded in
   * State and the run continues.
   *
   * The run writes into `state` when the caller gives one, and into a new
   * State when not. A State belongs to one run: a caller with more than one
   * run of this Pipeline at a time gives each run its own.
   */
  async run(initial: P, state: State = new State()): Promise<P> {
    // The State is a local of this call, so two runs at the same time do not mix.
    this.#state = state; // the State of the run that started last
    const hooks = this.#hooks;
    const timed = this.#timing;
    let payload = initial.copy(); // the caller's value is not changed

    for (const hook of hooks) {
      const done = hook.before(null, payload);
      if (isThenable(done)) await done;
    }

    let failing: string | null = null; // the step that is running when an error escapes
    let started: number | null = null;
    try {
      for (const step of this.#steps) {
        const label = step.label;
        failing = null;
        started = null;

        if (step.kind === "tap") {
          try {
            const done = step.tap.observe(payload);
            if (isThenable(done)) await done;
          } catch (error) {
            state.recordError(label, error);
          }
          state.markExecuted(label);
          continue;
        }

        if (timed) started = performance.now();
        failing = label;
        for (const hook of hooks) {
          const done = hook.before(label, payload);
          if (isThenable(done)) await done;
        }

        if (step.kind === "pipeline") {
          payload = await step.pipeline.run(payload);
          state.markExecuted(label);
        } else if (step.kind === "valve" && !step.valve.predicate.test(payload)) {
          state.markSkipped(label);
        } else {
          const filter = step.kind === "valve" ? step.valve.filter : step.filter;
          const result = filter.call(payload);
          payload = isThenable(result) ? await result : result;
          state.markExecuted(label);
        }

        for (const hook of hooks) {
          const done = hook.after(label, payload);
          if (isThenable(done)) await done;
        }
        if (timed && started !== null) state.recordTiming(label, (performance.now() - started) / 1000);
        if (this.#lineage) payload._stamp?.(label);
      }
    } catch (error) {
      if (timed && started !== null && failing !== null) {
        state.recordTiming(failing, (performance.now() - started) / 1000);
      }
      if (failing !== null) {
        // The failing step first, then the pipeline: onError fires at both
        // levels, as before and after do.
        for (const hook of hooks) {
          const done = hook.onError(failing, error, payload);
          if (isThenable(done)) await done;
        }
      }
      for (const hook of hooks) {
        const done = hook.onError(null, error, payload);
        if (isThenable(done)) await done;
      }
      throw error;
    }

    for (const hook of hooks) {
      const done = hook.after(null, payload);
      if (isThenable(done)) await done;
    }
    return payload;
  }
}

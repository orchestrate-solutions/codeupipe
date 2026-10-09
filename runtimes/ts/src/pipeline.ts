/**
 * Pipeline: The Orchestrator
 *
 * Runs filters in sequence with hooks, taps, and state tracking.
 * run() is synchronous (the default); runAsync() / streamAsync() are the
 * opt-in async entry points (conformance/API.md).
 *
 * Core orchestration loop — sequential filter execution with hooks,
 * taps, valves, parallel fan-out, nested pipelines, and streaming.
 * The Govern layer (schemas, contracts, audit, dead-letter) is
 * Python-only.
 *
 * Features:
 *   - Sequential filter execution with hooks
 *   - Tap observation
 *   - Valve skip detection
 *   - Parallel fan-out/fan-in
 *   - Nested pipelines
 *   - Timing & lineage observation
 *   - Streaming via async generators
 *   - State tracking (executed, skipped, errors, timings, chunks)
 *   - describe() introspection
 */

import { Payload, type PayloadData } from "./payload.js";
import type { Filter } from "./filter.js";
import type { StreamFilter } from "./stream_filter.js";
import type { Tap } from "./tap.js";
import type { Hook } from "./hook.js";
import { State } from "./state.js";
import { TypedPipeline } from "./typed/pipeline.js";
import { AsyncStepInSyncRun } from "./async_step_in_sync_run.js";
import { AnonymousStep } from "./anonymous_step.js";
import { addSite, identify } from "./step_identity.js";
import type { TypedFilter } from "./typed/filter.js";

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

type StepType = "filter" | "tap" | "parallel" | "pipeline";

type ParallelGroup = { filters: Filter[]; names: (string | null)[] };

type Step = {
  /** The step's identity (conformance/API.md, "Step identity"). */
  name: string;
  step: Filter | Tap | ParallelGroup | Pipeline;
  type: StepType;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isStreamFilter(step: unknown): step is StreamFilter {
  return (
    typeof step === "object" &&
    step !== null &&
    "stream" in step &&
    typeof (step as StreamFilter).stream === "function"
  );
}

function isParallelGroup(step: unknown): step is ParallelGroup {
  return (
    typeof step === "object" &&
    step !== null &&
    "filters" in step &&
    Array.isArray((step as ParallelGroup).filters)
  );
}

/** Steps have no names (API contract): an extra argument is a leftover name. */
function noName(args: IArguments, method: string): void {
  if (args.length > 1) {
    throw new TypeError(
      `${method}() takes no step name: a step is identified by its filter (conformance/API.md, "Step identity")`,
    );
  }
}

function isPipeline(step: unknown): step is Pipeline {
  return step instanceof Pipeline;
}

function isAsyncFunction(fn: unknown): boolean {
  return typeof fn === "function" && fn.constructor?.name === "AsyncFunction";
}

function isThenable(value: unknown): value is PromiseLike<unknown> {
  return value != null && typeof (value as { then?: unknown }).then === "function";
}

/** A sync step's result, or AsyncStepInSyncRun if it returned a Promise. */
function syncResult<T>(value: T | Promise<T>, step: string): T {
  if (isThenable(value)) {
    (value as Promise<T>).catch(() => undefined); // never an unhandled rejection
    throw new AsyncStepInSyncRun(
      `step '${step}' returned a Promise inside run(); use runAsync() for async steps`,
    );
  }
  return value as T;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function invoke(fn: (...args: any[]) => any, ...args: any[]): Promise<void> {
  const result = fn(...args);
  if (result instanceof Promise) {
    await result;
  }
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

/**
 * Orchestrator — runs filters in sequence with hooks, taps, and state
 * tracking.
 *
 * Build a pipeline by adding filters, taps, and hooks. Run it with
 * `.run(payload)`. After execution, inspect `.state` for metadata.
 */
export class Pipeline<
  TIn extends PayloadData = PayloadData,
  TOut extends PayloadData = PayloadData,
> {
  private _steps: Step[] = [];
  private _hooks: Hook[] = [];
  private _state: State = new State();
  private _observeTiming = false;
  private _observeLineage = false;
  private _disabledTaps: Set<string> = new Set();
  private _occurrences: Map<string, number> = new Map();
  private _stepSites: Record<string, string> = {};

  // -----------------------------------------------------------------------
  // Builder API
  // -----------------------------------------------------------------------

  /** Access pipeline execution state after run(). */
  get state(): State {
    return this._state;
  }

  /** Each step's identity, in order. */
  get identities(): string[] {
    return this._steps.map((s) => s.name);
  }

  /** identity -> `file:line` of the add call (extra detail, not identity). */
  get stepSites(): Record<string, string> {
    return { ...this._stepSites };
  }

  /** Derive a step's identity; number it from its second use. */
  private _identity(base: string): string {
    const count = (this._occurrences.get(base) ?? 0) + 1;
    this._occurrences.set(base, count);
    const identity = count === 1 ? base : `${base}#${count}`;
    this._stepSites[identity] = addSite();
    return identity;
  }

  /** Add a filter (or Valve) to the pipeline. */
  addFilter(filter: Filter): this {
    noName(arguments, "addFilter");
    this._steps.push({ name: this._identity(identify(filter, "filter")), step: filter, type: "filter" });
    return this;
  }

  /** Add a tap (observation point) to the pipeline. */
  addTap(tap: Tap): this {
    noName(arguments, "addTap");
    this._steps.push({ name: this._identity(identify(tap, "tap")), step: tap, type: "tap" });
    return this;
  }

  /** Attach a lifecycle hook. */
  useHook(hook: Hook): this {
    this._hooks.push(hook);
    return this;
  }

  /** Add a parallel fan-out/fan-in group of filters: `parallel[<identities>]`. */
  addParallel(filters: Filter[]): this {
    noName(arguments, "addParallel");
    const names = filters.map((f) => identify(f, "filter"));
    this._steps.push({
      name: this._identity(`parallel[${names.join(",")}]`),
      step: { filters, names },
      type: "parallel",
    });
    return this;
  }

  /** Nest a named Pipeline subclass as a single step inside this Pipeline. */
  addPipeline(pipeline: Pipeline): this {
    noName(arguments, "addPipeline");
    if (Object.getPrototypeOf(pipeline) === Pipeline.prototype) {
      throw new AnonymousStep(
        "A nested pipeline must be a named Pipeline subclass (class UserOnboarding extends Pipeline {}), " +
          "identified like a filter. A plain new Pipeline() can only run at the top level.",
      );
    }
    this._steps.push({ name: this._identity(identify(pipeline, "pipeline")), step: pipeline, type: "pipeline" });
    return this;
  }

  /** Enable observation features (timing, lineage tracking). */
  observe(options?: { timing?: boolean; lineage?: boolean }): this {
    this._observeTiming = options?.timing ?? true;
    this._observeLineage = options?.lineage ?? false;
    return this;
  }

  /** Disable specific taps, by identity, at runtime. */
  disableTaps(...names: string[]): this {
    for (const n of names) this._disabledTaps.add(n);
    return this;
  }

  /** Re-enable previously disabled taps. */
  enableTaps(...names: string[]): this {
    for (const n of names) this._disabledTaps.delete(n);
    return this;
  }

  // -----------------------------------------------------------------------
  // Filter protocol — allows nesting
  // -----------------------------------------------------------------------

  /** Filter protocol: a Pipeline used as a step runs synchronously. */
  call(payload: Payload<TIn>): Payload<TOut> {
    return this.run(payload);
  }

  /** Async Filter protocol, for use inside `runAsync()`. */
  async callAsync(payload: Payload<TIn>): Promise<Payload<TOut>> {
    return this.runAsync(payload);
  }

  // -----------------------------------------------------------------------
  // Batch execution
  // -----------------------------------------------------------------------

  /**
   * Fast path check: pipeline is a plain sequence of Filters with no
   * hooks, no observation, no taps, no parallel, no nested, no stream.
   * The common case — delegated to TypedPipeline<Payload> under the hood.
   */
  private _canRunFast(): boolean {
    if (this._hooks.length > 0) return false;
    if (this._observeTiming || this._observeLineage) return false;
    if (this._disabledTaps.size > 0) return false;
    for (const s of this._steps) {
      if (s.type !== "filter") return false;
      if (isStreamFilter(s.step)) return false;
    }
    return true;
  }

  private async _runFast(
    initialPayload: Payload<TIn>,
  ): Promise<Payload<TOut>> {
    const typed = new TypedPipeline<Payload<PayloadData>>();
    for (const { name, step } of this._steps) {
      typed.addFilter(step as unknown as TypedFilter<Payload<PayloadData>>, name);
    }
    try {
      const out = await typed.run(initialPayload as Payload<PayloadData>);
      return out as Payload<TOut>;
    } finally {
      // Adopt the typed pipeline's state so external observers see the same
      // executed/skipped bookkeeping, including after a failed run.
      this._state = typed.state;
    }
  }

  /**
   * Run a Tap on Plane B: its failure never halts the pipeline. The error is
   * recorded in state.errors under the Tap's name and the payload continues.
   * Same contract in every runtime (conformance/cases/tap.json).
   */
  private async _observe(name: string, tap: Tap, payload: Payload): Promise<void> {
    try {
      await invoke(tap.observe.bind(tap), payload);
    } catch (e) {
      this._state.recordError(name, e instanceof Error ? e : new Error(String(e)));
    }
  }

  private _rejectStreamFilters(): void {
    for (const { name, step, type } of this._steps) {
      if (type === "filter" && isStreamFilter(step)) {
        throw new Error(
          `Pipeline contains StreamFilter '${name}'. ` +
            `Use pipeline.streamAsync() with an async iterable instead.`,
        );
      }
    }
  }

  /** Name of the first `async` step, tap, or hook, or null if all are sync. */
  private _firstAsyncOffender(): string | null {
    for (const hook of this._hooks) {
      if (isAsyncFunction(hook.before) || isAsyncFunction(hook.after) || isAsyncFunction(hook.onError)) {
        return `hook ${hook.constructor.name}`;
      }
    }
    for (const { name, step, type } of this._steps) {
      if (type === "tap" && isAsyncFunction((step as Tap).observe)) return name;
      if (type === "pipeline" && isPipeline(step)) {
        const inner = step._firstAsyncOffender();
        if (inner !== null) return `${name}.${inner}`;
      }
      if (type === "parallel" && isParallelGroup(step)) {
        if (step.filters.some((f) => isAsyncFunction(f.call))) return name;
      }
      if (type === "filter") {
        if (isAsyncFunction((step as Filter).call)) return name;
        const inner = (step as unknown as { _inner?: Filter })._inner;
        if (inner && isAsyncFunction(inner.call)) return name;
      }
    }
    return null;
  }

  /** Sync counterpart of `_observe`: a Tap failure never halts the run. */
  private _observeSync(name: string, tap: Tap, payload: Payload): void {
    try {
      const result: unknown = tap.observe(payload);
      if (isThenable(result)) {
        (result as Promise<unknown>).catch(() => undefined);
        throw new AsyncStepInSyncRun(`tap '${name}' returned a Promise inside run()`);
      }
    } catch (e) {
      this._state.recordError(name, e instanceof Error ? e : new Error(String(e)));
    }
  }

  /**
   * Execute synchronously (the default). Never awaits: an `async` filter,
   * tap, or hook, or a step that returns a Promise, raises
   * `AsyncStepInSyncRun`; use `runAsync()` for those pipelines.
   */
  run(initialPayload: Payload<TIn>): Payload<TOut> {
    this._rejectStreamFilters();
    const offender = this._firstAsyncOffender();
    if (offender !== null) {
      throw new AsyncStepInSyncRun(
        `cannot run async step '${offender}' inside run(). Use runAsync(), or replace it with a sync step.`,
      );
    }

    this._state = new State();
    let payload: Payload = initialPayload;

    for (const hook of this._hooks) {
      if (hook.before) syncResult(hook.before(null, payload), "hook");
    }

    let stepName: string | undefined;
    let stepT0: number | undefined;
    let failing: string | null = null; // the step running when an error escapes

    try {
      for (const { name, step, type } of this._steps) {
        stepName = name;
        stepT0 = undefined;
        failing = null;

        if (type === "tap") {
          if (this._disabledTaps.has(name)) {
            this._state.markSkipped(name);
            continue;
          }
          this._observeSync(name, step as Tap, payload);
          this._state.markExecuted(name);
          continue;
        }

        stepT0 = performance.now();
        failing = name;

        if (type === "parallel" && isParallelGroup(step)) {
          const results = step.filters.map((f) => syncResult(f.call(payload), name));
          for (const result of results) {
            payload = payload.merge(result);
          }
          this._state.markExecuted(name);
        } else if (type === "pipeline" && isPipeline(step)) {
          for (const hook of this._hooks) {
            if (hook.before) syncResult(hook.before(name, payload), "hook");
          }
          payload = step.run(payload);
          this._state.markExecuted(name);
          for (const hook of this._hooks) {
            if (hook.after) syncResult(hook.after(name, payload), "hook");
          }
        } else {
          for (const hook of this._hooks) {
            if (hook.before) syncResult(hook.before(name, payload), "hook");
          }
          payload = syncResult((step as Filter).call(payload), name);
          if ((step as unknown as { _lastSkipped?: boolean })._lastSkipped) {
            this._state.markSkipped(name);
          } else {
            this._state.markExecuted(name);
          }
          for (const hook of this._hooks) {
            if (hook.after) syncResult(hook.after(name, payload), "hook");
          }
        }

        const duration = (performance.now() - stepT0) / 1000;
        if (this._observeTiming) this._state.recordTiming(name, duration);
        if (this._observeLineage) payload = payload._stamp(name);
      }
    } catch (e) {
      if (stepT0 !== undefined && stepName !== undefined && this._observeTiming) {
        this._state.recordTiming(stepName, (performance.now() - stepT0) / 1000);
      }
      const error = e instanceof Error ? e : new Error(String(e));
      // The failing step first, then the pipeline (conformance/cases/hook.json).
      if (failing !== null) {
        for (const hook of this._hooks) {
          if (hook.onError) syncResult(hook.onError(failing, error, payload), "hook");
        }
      }
      for (const hook of this._hooks) {
        if (hook.onError) syncResult(hook.onError(null, error, payload), "hook");
      }
      throw e;
    }

    for (const hook of this._hooks) {
      if (hook.after) syncResult(hook.after(null, payload), "hook");
    }
    return payload as unknown as Payload<TOut>;
  }

  /** Execute with async steps allowed (opt-in). `run()` is the default. */
  async runAsync(initialPayload: Payload<TIn>): Promise<Payload<TOut>> {
    this._rejectStreamFilters();

    if (this._canRunFast()) return this._runFast(initialPayload);

    this._state = new State();
    let payload: Payload = initialPayload;

    // Hook: pipeline start
    for (const hook of this._hooks) {
      if (hook.before) await invoke(hook.before.bind(hook), null, payload);
    }

    let stepName: string | undefined;
    let stepT0: number | undefined;
    let failing: string | null = null; // the step running when an error escapes

    try {
      for (const { name, step, type } of this._steps) {
        stepName = name;
        stepT0 = undefined;
        failing = null;

        // --- Tap ---
        if (type === "tap") {
          if (this._disabledTaps.has(name)) {
            this._state.markSkipped(name);
            continue;
          }
          await this._observe(name, step as Tap, payload);
          this._state.markExecuted(name);
          continue;
        }

        stepT0 = performance.now();
        failing = name;

        // --- Parallel ---
        if (type === "parallel" && isParallelGroup(step)) {
          const results = await Promise.all(
            step.filters.map((f) => Promise.resolve(f.call(payload))),
          );
          for (const result of results) {
            payload = payload.merge(result);
          }
          this._state.markExecuted(name);
        }
        // --- Nested Pipeline ---
        else if (type === "pipeline" && isPipeline(step)) {
          for (const hook of this._hooks) {
            if (hook.before) await invoke(hook.before.bind(hook), name, payload);
          }
          payload = await step.runAsync(payload);
          this._state.markExecuted(name);
          for (const hook of this._hooks) {
            if (hook.after) await invoke(hook.after.bind(hook), name, payload);
          }
        }
        // --- Filter / Valve ---
        else {
          for (const hook of this._hooks) {
            if (hook.before) await invoke(hook.before.bind(hook), name, payload);
          }

          payload = await (step as Filter).call(payload);

          // Valve skip detection
          if (
            "_lastSkipped" in (step as unknown as Record<string, unknown>) &&
            (step as unknown as { _lastSkipped: boolean })._lastSkipped
          ) {
            this._state.markSkipped(name);
          } else {
            this._state.markExecuted(name);
          }

          for (const hook of this._hooks) {
            if (hook.after) await invoke(hook.after.bind(hook), name, payload);
          }
        }

        // Post-step instrumentation
        const duration = (performance.now() - stepT0) / 1000;
        if (this._observeTiming) {
          this._state.recordTiming(name, duration);
        }
        if (this._observeLineage) {
          payload = payload._stamp(name);
        }
      }
    } catch (e) {
      if (stepT0 !== undefined && stepName !== undefined) {
        const duration = (performance.now() - stepT0) / 1000;
        if (this._observeTiming) {
          this._state.recordTiming(stepName, duration);
        }
      }
      const error = e instanceof Error ? e : new Error(String(e));
      // The failing step first, then the pipeline: onError mirrors
      // before/after, which fire at both levels (conformance/cases/hook.json).
      if (failing !== null) {
        for (const hook of this._hooks) {
          if (hook.onError) await invoke(hook.onError.bind(hook), failing, error, payload);
        }
      }
      for (const hook of this._hooks) {
        if (hook.onError) await invoke(hook.onError.bind(hook), null, error, payload);
      }
      throw e;
    }

    // Hook: pipeline end
    for (const hook of this._hooks) {
      if (hook.after) await invoke(hook.after.bind(hook), null, payload);
    }

    return payload as unknown as Payload<TOut>;
  }

  // -----------------------------------------------------------------------
  // Introspection
  // -----------------------------------------------------------------------

  /** Return a machine-readable tree of the pipeline structure. */
  describe(): {
    steps: Record<string, unknown>[];
    hooks: string[];
    step_count: number;
  } {
    const steps: Record<string, unknown>[] = [];

    for (const { name, step, type } of this._steps) {
      if (type === "parallel" && isParallelGroup(step)) {
        steps.push({
          name,
          type: "parallel",
          filters: step.filters.map((f, i) => ({
            name: step.names[i] ?? f.constructor.name,
            type: "filter",
          })),
        });
      } else if (type === "pipeline" && isPipeline(step)) {
        steps.push({
          name,
          type: "pipeline",
          children: step.describe().steps,
        });
      } else {
        steps.push({
          name,
          type,
          class: (step as object).constructor.name,
        });
      }
    }

    return {
      steps,
      hooks: this._hooks.map((h) => h.constructor.name),
      step_count: steps.length,
    };
  }

  // -----------------------------------------------------------------------
  // Streaming
  // -----------------------------------------------------------------------

  /** Stream payloads through the pipeline, one chunk at a time. */
  async *streamAsync(
    source: AsyncIterable<Payload<TIn>>,
  ): AsyncGenerator<Payload<TOut>> {
    this._state = new State();

    const sentinel = new Payload();
    for (const hook of this._hooks) {
      if (hook.before) await invoke(hook.before.bind(hook), null, sentinel);
    }

    try {
      let current: AsyncIterable<Payload> = source;

      for (const { name, step, type } of this._steps) {
        current = this._wrapStep(current, name, step, type);
      }

      for await (const result of current) {
        yield result as Payload<TOut>;
      }
    } catch (e) {
      const error = e instanceof Error ? e : new Error(String(e));
      for (const hook of this._hooks) {
        if (hook.onError) await invoke(hook.onError.bind(hook), null, error, sentinel);
      }
      throw e;
    }

    for (const hook of this._hooks) {
      if (hook.after) await invoke(hook.after.bind(hook), null, sentinel);
    }
  }

  private async *_wrapStep(
    upstream: AsyncIterable<Payload>,
    name: string,
    step: Filter | Tap | ParallelGroup | Pipeline,
    stepType: StepType,
  ): AsyncGenerator<Payload> {
    // --- Tap ---
    if (stepType === "tap") {
      if (this._disabledTaps.has(name)) {
        this._state.markSkipped(name);
        for await (const chunk of upstream) {
          yield chunk;
        }
        return;
      }
      if (!this._state.executed.includes(name)) {
        this._state.markExecuted(name);
      }
      for await (const chunk of upstream) {
        await this._observe(name, step as Tap, chunk);
        this._state.incrementChunks(name);
        yield chunk;
      }
      return;
    }

    // --- StreamFilter ---
    if (stepType === "filter" && isStreamFilter(step)) {
      if (!this._state.executed.includes(name)) {
        this._state.markExecuted(name);
      }
      for await (const chunk of upstream) {
        for await (const out of step.stream(chunk)) {
          this._state.incrementChunks(name);
          yield out;
        }
      }
      return;
    }

    // --- Regular Filter ---
    if (stepType === "filter") {
      if (!this._state.executed.includes(name)) {
        this._state.markExecuted(name);
      }
      for await (const chunk of upstream) {
        const result = await (step as Filter).call(chunk);
        this._state.incrementChunks(name);
        yield result;
      }
      return;
    }

    // --- Parallel ---
    if (stepType === "parallel" && isParallelGroup(step)) {
      if (!this._state.executed.includes(name)) {
        this._state.markExecuted(name);
      }
      for await (const chunk of upstream) {
        const results = await Promise.all(
          step.filters.map((f) => f.call(chunk)),
        );
        let merged = chunk;
        for (const r of results) {
          merged = merged.merge(r);
        }
        this._state.incrementChunks(name);
        yield merged;
      }
      return;
    }

    // --- Nested Pipeline ---
    if (stepType === "pipeline" && isPipeline(step)) {
      if (!this._state.executed.includes(name)) {
        this._state.markExecuted(name);
      }
      for await (const chunk of upstream) {
        const result = await step.runAsync(chunk);
        this._state.incrementChunks(name);
        yield result;
      }
      return;
    }
  }
}

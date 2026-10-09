/**
 * @codeupipe/core — TypeScript runtime
 *
 * The 8 core CUP primitives for web and browser pipelines.
 * Zero dependencies. Same mental model, same API shape across
 * all runtimes (Python, TypeScript, Rust, Go, C#).
 */

export { Payload, MutablePayload, type PayloadData } from "./payload.js";
export { type Filter } from "./filter.js";
export { type StreamFilter } from "./stream_filter.js";
export { type Tap } from "./tap.js";
export { type Hook } from "./hook.js";
export { State } from "./state.js";
export { Valve } from "./valve.js";
export { type Predicate } from "./predicate.js";
export { Pipeline } from "./pipeline.js";
export { AsyncStepInSyncRun } from "./async_step_in_sync_run.js";
export { AnonymousStep } from "./anonymous_step.js";

// Typed pipeline — opt-in, compile-time schema
export * as typed from "./typed/index.js";

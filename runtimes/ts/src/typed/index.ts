/**
 * Typed pipeline — compile-time schema via TypeScript generics.
 *
 * `TypedPipeline<Ctx>` is a parallel API to `Pipeline`:
 * - Same seven primitives (Filter, Tap, Valve, Hook, State, Payload, Pipeline)
 * - `Ctx` is your payload type, known at authoring time
 * - No dict — the payload IS the type
 *
 * Dynamic escape hatch: use `Ctx = Record<string, unknown>` (or `any`) if
 * you truly need a dynamic bag of keys.
 */

export type { TypedFilter } from "./filter.js";
export type { TypedTap } from "./tap.js";
export type { TypedHook } from "./hook.js";
export { TypedValve } from "./valve.js";
export { TypedPipeline } from "./pipeline.js";

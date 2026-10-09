/**
 * Step identity, runtime side (conformance/API.md, "Step identity").
 *
 * A step is identified by the declaration of the code that runs it:
 * `<package>/<source path>#<Name>`. JavaScript cannot derive that at
 * runtime, so codeupipe's build step stamps every top-level class and
 * function declaration (identity/stamp.ts); this module reads the stamp.
 *
 * Only a declaration's OWN stamp counts: a subclass declared inside a
 * function would otherwise inherit its parent's identity through the
 * constructor's prototype chain.
 */

import { AnonymousStep } from "./anonymous_step.js";

const IDENTITY = Symbol.for("cup.identity");

const FIX =
  "Declare it as a top-level class (or, for a Valve predicate, a top-level function) " +
  "so it has a stable identity and can be tested on its own, and build with codeupipe's " +
  "identity step (identity/vite_plugin.ts, identity/bun_preload.ts, or identity/stamp_dist.ts after tsc).";

/** The stamped identity of a class or function, if it has its own. */
export function stampOf(target: unknown): string | undefined {
  if ((typeof target !== "function" && typeof target !== "object") || target === null) return undefined;
  return Object.prototype.hasOwnProperty.call(target, IDENTITY)
    ? ((target as Record<symbol, string>)[IDENTITY] as string)
    : undefined;
}

function describe(target: unknown): string {
  if (typeof target === "function") {
    if (target.prototype === undefined) return `an arrow function (${target.name || "anonymous"})`;
    return `${target.name || "an anonymous class or function"}`;
  }
  return String(target);
}

/** The identity of a code declaration (a class or a function), or AnonymousStep. */
export function symbolOf(target: unknown, what: string): string {
  const stamp = stampOf(target);
  if (stamp) return stamp;
  throw new AnonymousStep(`${what} ${describe(target)} has no step identity. ${FIX}`);
}

/**
 * The identity of a Valve predicate: an object with `test(payload)`,
 * identified by its class's stamp. A function is not a predicate object.
 */
export function predicateSymbol(predicate: unknown): string {
  if (
    predicate === null ||
    typeof predicate !== "object" ||
    typeof (predicate as { test?: unknown }).test !== "function"
  ) {
    const what = typeof predicate === "function" ? describe(predicate) : String(predicate);
    throw new AnonymousStep(
      `Valve predicate ${what} is not a predicate object. Declare a top-level class with ` +
        "test(payload): boolean (configuration on the instance) and pass an instance.",
    );
  }
  const ctor = (predicate as { constructor?: unknown }).constructor;
  if (ctor === Object || ctor === undefined) {
    throw new AnonymousStep(`Valve predicate is an object literal, which has no identity. ${FIX}`);
  }
  return symbolOf(ctor, "Valve predicate");
}

/**
 * The identity of a step, before any `#n` occurrence number.
 *
 * kind: "filter", "tap" or "pipeline". A Valve is identified by its inner
 * filter. (Pipeline.addPipeline refuses a plain, unnamed Pipeline itself.)
 */
export function identify(step: unknown, kind: "filter" | "tap" | "pipeline"): string {
  if (step !== null && typeof step === "object") {
    const inner = (step as { _inner?: unknown; _predicate?: unknown })._inner;
    if (inner !== undefined && "_predicate" in (step as object)) return identify(inner, "filter");
    const ctor = (step as { constructor?: unknown }).constructor;
    if (ctor === Object || ctor === undefined) {
      throw new AnonymousStep(`${kind} is an object literal, which has no step identity. ${FIX}`);
    }
    return symbolOf(ctor, kind === "pipeline" ? "Nested pipeline" : kind === "tap" ? "Tap" : "Filter");
  }
  return symbolOf(step, kind);
}

/** `file:line` of the code that called an add method (extra detail, not identity). */
export function addSite(): string {
  const lines = (new Error().stack ?? "").split("\n");
  // [0] "Error", [1] addSite, [2] Pipeline._identity, [3] Pipeline.addX, [4] the caller
  const caller = lines[4] ?? "";
  const match = caller.match(/\(?((?:file:\/\/)?[^()\s]+:\d+):\d+\)?\s*$/);
  return match?.[1] ?? caller.trim();
}

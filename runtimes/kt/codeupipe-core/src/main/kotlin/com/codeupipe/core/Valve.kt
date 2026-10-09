package com.codeupipe.core

/**
 * Valve: Conditional Flow Control
 *
 * Wraps a [Filter] with a predicate — the inner filter only executes
 * when the predicate evaluates to true. Otherwise the payload passes
 * through unchanged.
 *
 * Implements [Filter] so it can be used anywhere a Filter is expected.
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
class Valve(
    internal val inner: Filter,
    private val predicate: Predicate,
) : Filter {

    /** The predicate's identity (detail: a Valve is identified by its inner filter). */
    val predicateSymbol: String = StepIdentity.symbolOf(predicate, "Valve predicate")

    /** Whether the last call was skipped. Used by Pipeline for state. */
    internal var lastSkipped: Boolean = false
        private set

    override fun call(payload: Payload): Payload {
        return if (predicate.test(payload)) {
            lastSkipped = false
            inner.call(payload)
        } else {
            lastSkipped = true
            payload
        }
    }
}

package com.codeupipe.core

/**
 * Tap: Observation Point
 *
 * Non-modifying observer. Receives payload for inspection (logging,
 * metrics, debugging) but never modifies it. The pipeline calls
 * [observe] and discards the return value.
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
fun interface Tap {
    fun observe(payload: Payload)
}

package com.codeupipe.core

/**
 * Hook: Lifecycle Callbacks
 *
 * Before/after/onError callbacks that fire around filter execution.
 * All methods are optional — override what you need.
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
interface Hook {
    /** Before step [name], or before the pipeline starts (`null`). */
    fun before(name: String?, payload: Payload) {}

    /** After step [name], or after the pipeline ends (`null`). */
    fun after(name: String?, payload: Payload) {}

    /** For the failing step, then for the pipeline (`null`). */
    fun onError(name: String?, error: Exception, payload: Payload) {}
}

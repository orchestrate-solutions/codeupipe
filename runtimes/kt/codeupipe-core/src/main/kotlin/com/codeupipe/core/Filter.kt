package com.codeupipe.core

/**
 * Filter: The Processing Unit
 *
 * Takes a Payload in, processes it, and returns a (potentially
 * transformed) Payload out.
 *
 * Kotlin filters are synchronous by default — use suspend functions
 * in coroutine contexts via [SuspendFilter].
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
fun interface Filter {
    fun call(payload: Payload): Payload
}

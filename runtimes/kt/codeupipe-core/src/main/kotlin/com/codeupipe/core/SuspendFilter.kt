package com.codeupipe.core

/**
 * SuspendFilter: Async Processing Unit
 *
 * Like [Filter] but supports Kotlin coroutines via suspend.
 * Use when the filter needs to do async I/O (network, disk, etc.).
 */
fun interface SuspendFilter {
    suspend fun call(payload: Payload): Payload
}

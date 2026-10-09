package com.codeupipe.core

/**
 * StreamFilter: Chunk-at-a-Time Processing
 *
 * Processes one Payload chunk and returns zero or more output chunks.
 * Enables filtering (drop), mapping (1→1), and fan-out (1→N) at
 * constant memory.
 *
 * See also: Python, TypeScript, Rust, Go implementations.
 */
fun interface StreamFilter {
    /**
     * Process a chunk. Returns a list of output payloads.
     * - Empty list = drop the chunk (filter)
     * - Single element = 1:1 transform (map)
     * - Multiple elements = fan-out
     */
    fun stream(chunk: Payload): List<Payload>
}

package com.codeupipe.core

/**
 * State: Pipeline Execution Metadata
 *
 * Tracks what happened during pipeline execution — which filters ran,
 * which were skipped, timing data, and errors encountered.
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
class State {
    val executed: MutableList<String> = mutableListOf()
    val skipped: MutableList<String> = mutableListOf()
    val errors: MutableList<Pair<String, Exception>> = mutableListOf()
    val metadata: MutableMap<String, Any?> = mutableMapOf()
    val timings: MutableMap<String, Double> = mutableMapOf()
    val chunksProcessed: MutableMap<String, Int> = mutableMapOf()

    /** Record that a filter executed. */
    fun markExecuted(name: String) {
        executed.add(name)
    }

    /** Record that a filter was skipped. */
    fun markSkipped(name: String) {
        skipped.add(name)
    }

    /** Record step execution duration in seconds. */
    fun recordTiming(name: String, durationSeconds: Double) {
        timings[name] = durationSeconds
    }

    /** Record an error from a filter. */
    fun recordError(name: String, error: Exception) {
        errors.add(name to error)
    }

    /** Increment the chunk counter for a streaming step. */
    fun incrementChunks(name: String, count: Int = 1) {
        chunksProcessed[name] = (chunksProcessed[name] ?: 0) + count
    }

    /** Store arbitrary metadata. */
    fun set(key: String, value: Any?) {
        metadata[key] = value
    }

    /** Read metadata. */
    @Suppress("UNCHECKED_CAST")
    fun <T> get(key: String): T? = metadata[key] as? T

    /** True if no errors were recorded. */
    val ok: Boolean get() = errors.isEmpty()

    /** Total number of steps (executed + skipped). */
    val totalSteps: Int get() = executed.size + skipped.size

    /** Reset all tracked state. */
    fun reset() {
        executed.clear()
        skipped.clear()
        errors.clear()
        metadata.clear()
        timings.clear()
        chunksProcessed.clear()
    }

    override fun toString(): String {
        return "State(executed=${executed.size}, skipped=${skipped.size}, errors=${errors.size})"
    }
}

package com.codeupipe.core

/**
 * Pipeline: The Orchestrator
 *
 * Runs filters in sequence with hooks, taps, and state tracking.
 * Sync-first design — ideal for Android main thread, game loops,
 * and real-time systems.
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
open class Pipeline {

    /** `name` is the step's identity (conformance/API.md, "Step identity"). */
    private sealed class Step(val name: String) {
        class FilterStep(name: String, val filter: Filter) : Step(name)
        class TapStep(name: String, val tap: Tap) : Step(name)
        class NestedStep(name: String, val pipeline: Pipeline) : Step(name)
    }

    private val steps = mutableListOf<Step>()
    private val hooks = mutableListOf<Hook>()
    private var _state = State()
    private var observeTiming = false
    private var observeLineage = false

    /** Access pipeline execution state after run(). */
    val state: State get() = _state

    // ── Builder API ─────────────────────────────────────────────────

    private val occurrences = mutableMapOf<String, Int>()
    private val sites = mutableMapOf<String, String>()

    /** Each step's identity, in order. */
    val identities: List<String> get() = steps.map { it.name }

    /** identity -> `File.kt:line` of the add call (detail, not identity). */
    val stepSites: Map<String, String> get() = sites.toMap()

    private fun identity(base: String): String {
        val n = (occurrences[base] ?: 0) + 1
        occurrences[base] = n
        val id = if (n == 1) base else "$base#$n"
        sites[id] = StepIdentity.addSite()
        return id
    }

    /** Add a filter (or [Valve]), identified by its class. */
    fun addFilter(filter: Filter): Pipeline {
        steps.add(Step.FilterStep(identity(StepIdentity.identify(filter, "Filter")), filter))
        return this
    }

    /** Add a tap (observation point), identified by its class. */
    fun addTap(tap: Tap): Pipeline {
        steps.add(Step.TapStep(identity(StepIdentity.identify(tap, "Tap")), tap))
        return this
    }

    /** Nest a named Pipeline subclass as one step. */
    fun addPipeline(pipeline: Pipeline): Pipeline {
        if (pipeline.javaClass == Pipeline::class.java) {
            throw AnonymousStep(
                "A nested pipeline must be a named Pipeline subclass (class Onboarding : Pipeline()), " +
                    "identified like a filter. A plain Pipeline() can only run at the top level.")
        }
        steps.add(Step.NestedStep(identity(StepIdentity.identify(pipeline, "Nested pipeline")), pipeline))
        return this
    }

    /** Add a lifecycle hook. */
    fun useHook(hook: Hook): Pipeline {
        hooks.add(hook)
        return this
    }

    /** Enable timing observation. */
    fun withTiming(): Pipeline {
        observeTiming = true
        return this
    }

    /** Enable lineage observation. */
    fun withLineage(): Pipeline {
        observeLineage = true
        return this
    }

    // ── Execution ───────────────────────────────────────────────────

    /** Run the pipeline synchronously. */
    fun run(payload: Payload): Payload {
        _state = State()
        var current = payload

        // Pipeline-level hook events use an empty name and wrap the
        // step-level ones; on a failure the failing step's onError (fired in
        // executeFilter) is followed by the pipeline's. Same contract in every
        // runtime: conformance/cases/hook.json.
        hooks.forEach { it.before(null, current) }
        try {
            for (step in steps) {
                current = executeStep(step, current)
            }
        } catch (e: Exception) {
            hooks.forEach { it.onError(null, e, current) }
            throw e
        }
        hooks.forEach { it.after(null, current) }

        return current
    }

    /** Streaming execution — process a sequence of chunks. */
    fun stream(chunks: Sequence<Payload>): Sequence<Payload> {
        return sequence {
            for (chunk in chunks) {
                var current = chunk
                for (step in steps) {
                    current = when (step) {
                        is Step.FilterStep -> {
                            if (step.filter is StreamFilter) {
                                val outputs = (step.filter as StreamFilter).stream(current)
                                _state.incrementChunks(step.name, outputs.size)
                                // For stream filters, yield all outputs
                                for (output in outputs) {
                                    yield(output)
                                }
                                continue
                            } else {
                                executeStep(step, current)
                            }
                        }
                        else -> executeStep(step, current)
                    }
                }
                yield(current)
            }
        }
    }

    /** Describe the pipeline structure. */
    fun describe(): List<Map<String, String>> {
        return steps.map { step ->
            mapOf(
                "name" to step.name,
                "type" to when (step) {
                    is Step.FilterStep -> when {
                        step.filter is Valve -> "valve"
                        step.filter is StreamFilter -> "stream_filter"
                        else -> "filter"
                    }
                    is Step.TapStep -> "tap"
                    is Step.NestedStep -> "pipeline"
                }
            )
        }
    }

    // ── Internal ────────────────────────────────────────────────────

    private fun executeStep(step: Step, payload: Payload): Payload {
        return when (step) {
            is Step.FilterStep -> executeFilter(step, payload)
            is Step.TapStep -> executeTap(step, payload)
            is Step.NestedStep -> executeNested(step, payload)
        }
    }

    private fun executeFilter(step: Step.FilterStep, payload: Payload): Payload {
        // Fire before hooks
        hooks.forEach { it.before(step.name, payload) }

        val startNs = if (observeTiming) System.nanoTime() else 0L

        return try {
            val result = step.filter.call(payload)

            // Check if valve skipped
            if (step.filter is Valve && (step.filter as Valve).lastSkipped) {
                _state.markSkipped(step.name)
            } else {
                _state.markExecuted(step.name)
            }

            // Record timing
            if (observeTiming) {
                val elapsed = (System.nanoTime() - startNs) / 1_000_000_000.0
                _state.recordTiming(step.name, elapsed)
            }

            // Stamp lineage
            val stamped = if (observeLineage) result.stamp(step.name) else result

            // Fire after hooks
            hooks.forEach { it.after(step.name, stamped) }

            stamped
        } catch (e: Exception) {
            _state.recordError(step.name, e)
            hooks.forEach { it.onError(step.name, e, payload) }
            throw e
        }
    }

    private fun executeTap(step: Step.TapStep, payload: Payload): Payload {
        // Plane B: a Tap failure never halts the pipeline, and is not hidden
        // either. The exception is recorded under the Tap's name and the Tap
        // counts as executed. Same contract in every runtime
        // (conformance/cases/tap.json).
        try {
            step.tap.observe(payload)
        } catch (e: Exception) {
            _state.recordError(step.name, e)
        }
        _state.markExecuted(step.name)
        return payload
    }

    private fun executeNested(step: Step.NestedStep, payload: Payload): Payload {
        val result = step.pipeline.run(payload)
        _state.markExecuted(step.name)
        return result
    }
}

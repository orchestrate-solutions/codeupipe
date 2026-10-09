package com.codeupipe.core

import kotlin.test.*

// Steps are top-level named classes: a step is identified by its class
// (conformance/API.md, "Step identity"), and lambdas have none.
private const val P = "com.codeupipe.core."

class SetKey(private val key: String, private val value: Any?) : Filter {
    override fun call(payload: Payload) = payload.insert(key, value)
}

class Increment(private val key: String) : Filter {
    override fun call(payload: Payload) = payload.insert(key, (payload.get<Int>(key) ?: 0) + 1)
}

class PassThrough : Filter {
    override fun call(payload: Payload) = payload
}

class Explode : Filter {
    override fun call(payload: Payload): Payload = throw RuntimeException("boom")
}

class Spy : Tap {
    var observed: Any? = null
    override fun observe(payload: Payload) { observed = payload.get<Int>("value") }
}

class SinkDown : Tap {
    override fun observe(payload: Payload) = throw RuntimeException("sink down")
}

class Quiet : Tap {
    override fun observe(payload: Payload) {}
}

object Allowed : Predicate {
    override fun test(payload: Payload) = payload.get<Boolean>("allow") == true
}

class SubPipeline : Pipeline()

class LogHook : Hook {
    val log = mutableListOf<String>()
    var caught: Exception? = null
    override fun before(name: String?, payload: Payload) { log.add("before:${name ?: ""}") }
    override fun after(name: String?, payload: Payload) { log.add("after:${name ?: ""}") }
    override fun onError(name: String?, error: Exception, payload: Payload) {
        caught = error
        log.add("error:${name ?: ""}")
    }
}

class PipelineTest {

    @Test
    fun `empty pipeline returns payload unchanged`() {
        val result = Pipeline().run(Payload(mapOf("x" to 1)))
        assertEquals(1, result.get<Int>("x"))
    }

    @Test
    fun `single filter transforms payload`() {
        val pipeline = Pipeline().addFilter(SetKey("added", true))
        val result = pipeline.run(Payload())
        assertEquals(true, result.get<Boolean>("added"))
        assertEquals(listOf("${P}SetKey"), pipeline.state.executed)
    }

    @Test
    fun `filters execute in sequence`() {
        val pipeline = Pipeline().addFilter(SetKey("step", 1)).addFilter(Increment("step"))
        val result = pipeline.run(Payload())
        assertEquals(2, result.get<Int>("step"))
        assertEquals(listOf("${P}SetKey", "${P}Increment"), pipeline.state.executed)
    }

    @Test
    fun `tap observes without modifying`() {
        val spy = Spy()
        val pipeline = Pipeline()
            .addFilter(SetKey("value", 42))
            .addTap(spy)
            .addFilter(SetKey("after_tap", true))
        val result = pipeline.run(Payload())
        assertEquals(42, spy.observed)
        assertEquals(42, result.get<Int>("value"))
        assertEquals(true, result.get<Boolean>("after_tap"))
    }

    @Test
    fun `valve skips when predicate is false`() {
        val pipeline = Pipeline().addFilter(Valve(inner = SetKey("ran", true), predicate = Allowed))

        val r1 = pipeline.run(Payload())
        assertNull(r1.get<Boolean>("ran"))
        assertEquals(listOf("${P}SetKey"), pipeline.state.skipped)

        val r2 = pipeline.run(Payload(mapOf("allow" to true)))
        assertEquals(true, r2.get<Boolean>("ran"))
        assertEquals(listOf("${P}SetKey"), pipeline.state.executed)
    }

    @Test
    fun `hook before and after fire`() {
        val hook = LogHook()
        Pipeline().useHook(hook).addFilter(PassThrough()).run(Payload())
        // pipeline-level events use an empty name, around the step-level ones
        // (the same contract in every runtime: conformance/cases/hook.json)
        assertEquals(listOf("before:", "before:${P}PassThrough", "after:${P}PassThrough", "after:"), hook.log)
    }

    @Test
    fun `hook onError fires for the failing step then the pipeline`() {
        val hook = LogHook()
        val pipeline = Pipeline().useHook(hook).addFilter(PassThrough()).addFilter(Explode())
        assertFailsWith<RuntimeException> { pipeline.run(Payload()) }
        assertEquals(
            listOf("before:", "before:${P}PassThrough", "after:${P}PassThrough",
                "before:${P}Explode", "error:${P}Explode", "error:"),
            hook.log)
    }

    @Test
    fun `hook onError fires on exception`() {
        val hook = LogHook()
        val pipeline = Pipeline().useHook(hook).addFilter(Explode())
        assertFailsWith<RuntimeException> { pipeline.run(Payload()) }
        assertEquals("boom", hook.caught?.message)
        assertTrue(pipeline.state.errors.any { it.first == "${P}Explode" })
    }

    @Test
    fun `timing records durations`() {
        val pipeline = Pipeline().withTiming().addFilter(SetKey("done", true))
        pipeline.run(Payload())
        assertTrue(pipeline.state.timings.getValue("${P}SetKey") >= 0.0)
    }

    @Test
    fun `lineage stamps steps`() {
        val pipeline = Pipeline().withLineage().addFilter(PassThrough()).addFilter(PassThrough())
        assertEquals(listOf("${P}PassThrough", "${P}PassThrough#2"), pipeline.run(Payload()).lineage)
    }

    @Test
    fun `nested pipeline runs inner steps`() {
        val inner = SubPipeline().addFilter(SetKey("inner", true))
        val outer = Pipeline().addFilter(SetKey("outer", true)).addPipeline(inner)
        val result = outer.run(Payload())
        assertEquals(true, result.get<Boolean>("outer"))
        assertEquals(true, result.get<Boolean>("inner"))
        assertEquals(listOf("${P}SetKey", "${P}SubPipeline"), outer.state.executed)
    }

    @Test
    fun `describe returns step metadata`() {
        val desc = Pipeline().addFilter(PassThrough()).addTap(Quiet()).describe()
        assertEquals(2, desc.size)
        assertEquals("${P}PassThrough", desc[0]["name"])
        assertEquals("filter", desc[0]["type"])
        assertEquals("${P}Quiet", desc[1]["name"])
        assertEquals("tap", desc[1]["type"])
    }

    @Test
    fun `state resets between runs`() {
        val pipeline = Pipeline().addFilter(PassThrough())
        pipeline.run(Payload())
        assertEquals(1, pipeline.state.executed.size)
        pipeline.run(Payload())
        assertEquals(1, pipeline.state.executed.size) // reset, not accumulated
    }

    // Plane B: a Tap failure never halts the pipeline. The exception is
    // recorded in state.errors under the Tap's identity and the Tap still
    // counts as executed. Same contract in every runtime: conformance/cases/tap.json.
    @Test
    fun `a throwing tap is contained and recorded`() {
        val pipeline = Pipeline()
            .addFilter(SetKey("a", 1))
            .addTap(SinkDown())
            .addFilter(SetKey("b", 2))

        val result = pipeline.run(Payload())

        assertEquals(2, result.get<Int>("b"))
        assertEquals(listOf("${P}SetKey", "${P}SinkDown", "${P}SetKey#2"), pipeline.state.executed)
        assertEquals(listOf("${P}SinkDown"), pipeline.state.errors.map { it.first })
    }
}

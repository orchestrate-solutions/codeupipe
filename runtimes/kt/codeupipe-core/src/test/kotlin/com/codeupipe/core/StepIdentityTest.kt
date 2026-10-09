package com.codeupipe.core

import kotlin.test.*

// Step identity (conformance/API.md): a step is identified by its filter's
// qualified class name, #n from its second use; no names. Anonymous steps
// (lambdas, anonymous objects, local classes) are refused when added.

private const val HERE = "com.codeupipe.core."

class IdInc : Filter {
    override fun call(payload: Payload) = payload.insert("n", (payload.get<Int>("n") ?: 0) + 1)
}

class IdBoom : Filter {
    override fun call(payload: Payload): Payload = throw RuntimeException("boom")
}

object IdAudit : Tap {
    override fun observe(payload: Payload) {}
}

object IdIsOn : Predicate {
    override fun test(payload: Payload) = payload.get<Boolean>("on") ?: false
}

/** A configurable predicate: a named class, its settings on the instance. */
class IdAtLeast(private val n: Int) : Predicate {
    override fun test(payload: Payload) = (payload.get<Int>("n") ?: 0) >= n
}

class IdOnboarding : Pipeline() {
    init { addFilter(IdInc()) }
}

class IdRecord : Hook {
    val events = mutableListOf<String>()
    override fun before(name: String?, payload: Payload) { events.add("before:${name ?: ""}") }
    override fun after(name: String?, payload: Payload) { events.add("after:${name ?: ""}") }
    override fun onError(name: String?, error: Exception, payload: Payload) { events.add("error:${name ?: ""}") }
}

class StepIdentityTest {
    @Test
    fun `state reports the qualified class name`() {
        val p = Pipeline().addFilter(IdInc())
        p.run(Payload())
        assertEquals(listOf("${HERE}IdInc"), p.state.executed)
    }

    @Test
    fun `reuse is numbered from the second occurrence`() {
        val p = Pipeline().addFilter(IdInc()).addFilter(IdInc()).addFilter(IdInc())
        assertEquals(listOf("${HERE}IdInc", "${HERE}IdInc#2", "${HERE}IdInc#3"), p.identities)
    }

    @Test
    fun `taps and hooks see identities`() {
        val hook = IdRecord()
        val p = Pipeline().addFilter(IdInc()).addTap(IdAudit).addFilter(IdBoom()).useHook(hook)
        assertFailsWith<RuntimeException> { p.run(Payload()) }
        assertEquals(listOf("${HERE}IdInc", "${HERE}IdAudit"), p.state.executed)
        assertEquals(
            listOf("before:", "before:${HERE}IdInc", "after:${HERE}IdInc",
                "before:${HERE}IdBoom", "error:${HERE}IdBoom", "error:"),
            hook.events)
    }

    @Test
    fun `a valve is identified by its inner filter`() {
        val p = Pipeline().addFilter(Valve(IdInc(), IdIsOn))
        p.run(Payload())
        assertEquals(listOf("${HERE}IdInc"), p.state.skipped)
    }

    @Test
    fun `a configurable predicate is a named class`() {
        val p = Pipeline().addFilter(Valve(IdInc(), IdAtLeast(5)))
        assertEquals(6, p.run(Payload(mapOf("n" to 5))).get<Int>("n"))
        assertEquals(1, p.run(Payload(mapOf("n" to 1))).get<Int>("n"))
    }

    @Test
    fun `a named pipeline subclass nests as one step`() {
        val outer = Pipeline().addFilter(IdInc()).addPipeline(IdOnboarding())
        assertEquals(2, outer.run(Payload()).get<Int>("n"))
        assertEquals(listOf("${HERE}IdInc", "${HERE}IdOnboarding"), outer.state.executed)
    }

    @Test
    fun `the add site is recorded`() {
        val p = Pipeline().addFilter(IdInc())
        assertTrue(p.stepSites.getValue("${HERE}IdInc").matches(Regex("""StepIdentityTest\.kt:\d+""")))
    }

    @Test
    fun `a SAM lambda filter is refused`() {
        val e = assertFailsWith<AnonymousStep> { Pipeline().addFilter(Filter { it }) }  // cup: allow-anonymous (a deliberate refusal test)
        assertTrue("top-level" in e.message!!)
    }

    @Test
    fun `an anonymous object tap is refused`() {
        assertFailsWith<AnonymousStep> {
            Pipeline().addTap(object : Tap { override fun observe(payload: Payload) {} })  // cup: allow-anonymous (a deliberate refusal test)
        }
    }

    @Test
    fun `a local class is refused`() {
        class Local : Filter { override fun call(payload: Payload) = payload }
        assertFailsWith<AnonymousStep> { Pipeline().addFilter(Local()) }  // cup: allow-anonymous (a deliberate refusal test)
    }

    @Test
    fun `a lambda predicate is refused`() {
        assertFailsWith<AnonymousStep> { Valve(IdInc(), Predicate { true }) }  // cup: allow-anonymous (a deliberate refusal test)
    }

    @Test
    fun `a plain Pipeline cannot be nested`() {
        val e = assertFailsWith<AnonymousStep> { Pipeline().addPipeline(Pipeline().addFilter(IdInc())) }  // cup: allow-anonymous (a deliberate refusal test)
        assertTrue("named Pipeline subclass" in e.message!!)
    }
}

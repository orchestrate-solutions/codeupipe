package com.codeupipe.core

import kotlin.test.*

/**
 * The CUP API contract, Kotlin side (conformance/API.md). Cross-runtime
 * semantics are in conformance/cases; these pin the Kotlin spellings.
 */
class ContractTest {
    @Test
    fun `hooks use useHook, receive identities, and pipeline-level events pass null`() {
        val hook = LogHook()
        Pipeline().useHook(hook).addFilter(PassThrough()).run(Payload())
        val id = "com.codeupipe.core.PassThrough"
        assertEquals(listOf("before:", "before:$id", "after:$id", "after:"), hook.log)
    }

    @Test
    fun `payload remove has toDict`() {
        val p = Payload(mapOf("a" to null, "b" to 2))
        assertTrue(p.has("a"))
        assertEquals(mapOf<String, Any?>("b" to 2), p.remove("a").toDict())
        assertTrue(p.has("a"))
    }

    @Test
    fun `a typed read of the wrong type fails at the read`() {
        val p = Payload(mapOf("s" to "not a number"))
        assertFailsWith<ClassCastException> { p.get<Int>("s") }
        assertEquals(5, p.get("missing", 5))
    }
}

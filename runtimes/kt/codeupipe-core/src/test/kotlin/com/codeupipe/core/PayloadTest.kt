package com.codeupipe.core

import kotlin.test.*

class PayloadTest {

    @Test
    fun `empty payload has no keys`() {
        val p = Payload()
        assertEquals(0, p.size)
        assertTrue(p.keys.isEmpty())
    }

    @Test
    fun `construct with data`() {
        val p = Payload(mapOf("a" to 1, "b" to "hello"))
        assertEquals(1, p.get<Int>("a"))
        assertEquals("hello", p.get<String>("b"))
        assertEquals(2, p.size)
    }

    @Test
    fun `get returns default when key absent`() {
        val p = Payload()
        assertNull(p.get<String>("missing"))
        assertEquals("fallback", p.get("missing", "fallback"))
    }

    @Test
    fun `require throws on missing key`() {
        val p = Payload()
        assertFailsWith<NoSuchElementException> {
            p.require<String>("nope")
        }
    }

    @Test
    fun `insert returns new payload`() {
        val p1 = Payload(mapOf("a" to 1))
        val p2 = p1.insert("b", 2)

        // Original unchanged
        assertNull(p1.get<Int>("b"))
        assertEquals(1, p1.size)

        // New payload has both
        assertEquals(1, p2.get<Int>("a"))
        assertEquals(2, p2.get<Int>("b"))
        assertEquals(2, p2.size)
    }

    @Test
    fun `insert overwrites existing key`() {
        val p1 = Payload(mapOf("a" to 1))
        val p2 = p1.insert("a", 99)

        assertEquals(1, p1.get<Int>("a"))
        assertEquals(99, p2.get<Int>("a"))
    }

    @Test
    fun `has checks key presence`() {
        val p = Payload(mapOf("exists" to true))
        assertTrue(p.has("exists"))
        assertFalse(p.has("missing"))
    }

    @Test
    fun `merge combines payloads`() {
        val p1 = Payload(mapOf("a" to 1, "b" to 2))
        val p2 = Payload(mapOf("b" to 99, "c" to 3))
        val merged = p1.merge(p2)

        assertEquals(1, merged.get<Int>("a"))
        assertEquals(99, merged.get<Int>("b")) // p2 wins
        assertEquals(3, merged.get<Int>("c"))
    }

    @Test
    fun `toMap returns copy`() {
        val p = Payload(mapOf("x" to 42))
        val map = p.toDict()
        assertEquals(42, map["x"])
    }

    @Test
    fun `withTrace sets trace ID`() {
        val p = Payload().withTrace("trace-123")
        assertEquals("trace-123", p.traceId)
    }

    @Test
    fun `stamp adds to lineage`() {
        val p = Payload()
            .stamp("step1")
            .stamp("step2")
        assertEquals(listOf("step1", "step2"), p.lineage)
    }

    @Test
    fun `withMutation creates mutable sibling`() {
        val p = Payload(mapOf("a" to 1))
        val mp = p.withMutation()
        mp.set("b", 2)

        // Original unchanged
        assertFalse(p.has("b"))

        // Mutable has both
        assertEquals(1, mp.get<Int>("a"))
        assertEquals(2, mp.get<Int>("b"))
    }

    @Test
    fun `mutable toImmutable freezes`() {
        val mp = MutablePayload(mutableMapOf("a" to 1 as Any?))
        mp.set("b", 2)
        val p = mp.toImmutable()

        assertEquals(1, p.get<Int>("a"))
        assertEquals(2, p.get<Int>("b"))
    }

    @Test
    fun `equality based on data`() {
        val p1 = Payload(mapOf("a" to 1))
        val p2 = Payload(mapOf("a" to 1))
        assertEquals(p1, p2)
    }
}

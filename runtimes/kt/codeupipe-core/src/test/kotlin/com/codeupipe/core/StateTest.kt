package com.codeupipe.core

import kotlin.test.*

class StateTest {

    @Test
    fun `fresh state is ok`() {
        val s = State()
        assertTrue(s.ok)
        assertEquals(0, s.totalSteps)
    }

    @Test
    fun `markExecuted tracks steps`() {
        val s = State()
        s.markExecuted("a")
        s.markExecuted("b")
        assertEquals(listOf("a", "b"), s.executed)
        assertEquals(2, s.totalSteps)
    }

    @Test
    fun `markSkipped tracks skips`() {
        val s = State()
        s.markSkipped("x")
        assertEquals(listOf("x"), s.skipped)
        assertEquals(1, s.totalSteps)
    }

    @Test
    fun `recordError makes state not ok`() {
        val s = State()
        assertTrue(s.ok)
        s.recordError("bad", RuntimeException("fail"))
        assertFalse(s.ok)
        assertEquals("bad", s.errors[0].first)
    }

    @Test
    fun `timing records`() {
        val s = State()
        s.recordTiming("step", 0.123)
        assertEquals(0.123, s.timings["step"])
    }

    @Test
    fun `chunks accumulate`() {
        val s = State()
        s.incrementChunks("stream", 5)
        s.incrementChunks("stream", 3)
        assertEquals(8, s.chunksProcessed["stream"])
    }

    @Test
    fun `metadata get and set`() {
        val s = State()
        s.set("key", "value")
        assertEquals("value", s.get<String>("key"))
    }

    @Test
    fun `reset clears everything`() {
        val s = State()
        s.markExecuted("a")
        s.recordError("b", RuntimeException("x"))
        s.recordTiming("c", 1.0)
        s.reset()

        assertTrue(s.ok)
        assertEquals(0, s.totalSteps)
        assertTrue(s.timings.isEmpty())
    }
}

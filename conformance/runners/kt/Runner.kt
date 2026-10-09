// Kotlin conformance runner: executes cases, reports what happened.
//
//   kotlinc runtimes/kt/codeupipe-core/src/main/kotlin/com/codeupipe/core/*.kt \
//           conformance/runners/kt/Runner.kt -include-runtime -d runner.jar
//   java -jar runner.jar < cases.json > results.json
//
// Mirrors conformance/runners/python/runner.py; conformance/run.py judges.
// Compiled with kotlinc directly (no Gradle download), so it carries a small
// JSON reader/writer instead of a library.
import com.codeupipe.core.Filter
import com.codeupipe.core.Hook
import com.codeupipe.core.Payload
import com.codeupipe.core.Pipeline
import com.codeupipe.core.Predicate
import com.codeupipe.core.Tap
import com.codeupipe.core.Valve

// ---------------------------------------------------------------------------
// JSON
// ---------------------------------------------------------------------------

class JsonReader(private val s: String) {
    private var i = 0

    private fun ws() { while (i < s.length && s[i].isWhitespace()) i++ }
    private fun peek(): Char { ws(); return if (i < s.length) s[i] else '\u0000' }
    private fun expect(c: Char) { if (peek() != c) error("json: expected $c at $i"); i++ }

    fun value(): Any? = when (peek()) {
        '{' -> obj()
        '[' -> arr()
        '"' -> str()
        't' -> { i += 4; true }
        'f' -> { i += 5; false }
        'n' -> { i += 4; null }
        else -> num()
    }

    private fun obj(): Map<String, Any?> {
        val m = LinkedHashMap<String, Any?>()
        expect('{')
        if (peek() == '}') { i++; return m }
        while (true) {
            val k = str(); expect(':'); m[k] = value()
            if (peek() == ',') { i++; continue }
            expect('}'); return m
        }
    }

    private fun arr(): List<Any?> {
        val l = ArrayList<Any?>()
        expect('[')
        if (peek() == ']') { i++; return l }
        while (true) {
            l.add(value())
            if (peek() == ',') { i++; continue }
            expect(']'); return l
        }
    }

    private fun str(): String {
        expect('"')
        val out = StringBuilder()
        while (s[i] != '"') {
            val c = s[i++]
            if (c != '\\') { out.append(c); continue }
            when (val e = s[i++]) {
                'n' -> out.append('\n'); 't' -> out.append('\t'); 'r' -> out.append('\r')
                'b' -> out.append('\b'); 'f' -> out.append('\u000c')
                'u' -> { out.append(s.substring(i, i + 4).toInt(16).toChar()); i += 4 }
                else -> out.append(e)
            }
        }
        i++
        return out.toString()
    }

    private fun num(): Any {
        ws()
        val start = i
        while (i < s.length && (s[i].isDigit() || s[i] in "-+.eE")) i++
        val text = s.substring(start, i)
        return if (text.any { it in ".eE" }) text.toDouble() else text.toLong()
    }
}

fun toJson(v: Any?): String = when (v) {
    null -> "null"
    is Boolean -> v.toString()
    is Int, is Long -> v.toString()
    is Double -> if (v.isFinite() && v == Math.floor(v) && Math.abs(v) < 1e15) v.toLong().toString() else v.toString()
    is Number -> v.toString()
    is String -> buildString {
        append('"')
        for (c in v) when {
            c == '"' -> append("\\\""); c == '\\' -> append("\\\\"); c == '\n' -> append("\\n")
            c == '\t' -> append("\\t"); c == '\r' -> append("\\r")
            c < ' ' -> append(String.format("\\u%04x", c.code))
            else -> append(c)
        }
        append('"')
    }
    is Map<*, *> -> v.entries.joinToString(",", "{", "}") { "${toJson(it.key.toString())}:${toJson(it.value)}" }
    is List<*> -> v.joinToString(",", "[", "]") { toJson(it) }
    else -> toJson(v.toString())
}

// ---------------------------------------------------------------------------
// reference vocabulary
// ---------------------------------------------------------------------------

class Unsupported(message: String) : Exception(message)

val taps = ArrayList<Any?>()
val hooks = ArrayList<Pair<String, String?>>()

@Suppress("UNCHECKED_CAST")
fun Map<String, Any?>.s(key: String) = this[key] as String

fun plus(a: Any?, b: Any?): Any = when {
    a is Long && b is Long -> a + b
    else -> (a as Number).toDouble() + (b as Number).toDouble()
}

fun truthy(v: Any?): Boolean = when (v) {
    null -> false
    is Boolean -> v
    is Long -> v != 0L
    is Double -> v != 0.0
    is String -> v.isNotEmpty()
    is List<*> -> v.isNotEmpty()
    is Map<*, *> -> v.isNotEmpty()
    else -> true
}

// Steps are top-level named classes: a step is identified by its class
// (conformance/API.md, "Step identity"); lambdas are refused.
class SetOp(private val key: String, private val value: Any?) : Filter {
    override fun call(payload: Payload) = payload.insert(key, value)
}
class CopyOp(private val from: String, private val to: String) : Filter {
    override fun call(payload: Payload) = payload.insert(to, payload.get<Any?>(from))
}
class AddOp(private val key: String, private val by: Any?) : Filter {
    override fun call(payload: Payload) = payload.insert(key, plus(payload.get<Any?>(key, 0L), by))
}
class AppendOp(private val key: String, private val value: Any?) : Filter {
    override fun call(payload: Payload): Payload {
        val current = payload.get<List<Any?>>(key) ?: emptyList()
        return payload.insert(key, current + listOf(value))
    }
}
class RemoveOp(private val key: String) : Filter {
    override fun call(payload: Payload) = payload.remove(key)
}
class MergeOp(private val value: Map<String, Any?>) : Filter {
    override fun call(payload: Payload) = payload.merge(Payload(value))
}
class HasOp(private val key: String, private val to: String) : Filter {
    override fun call(payload: Payload) = payload.insert(to, payload.has(key))
}
class MutateOp(private val key: String, private val value: Any?) : Filter {
    override fun call(payload: Payload) = payload.withMutation().set(key, value).toImmutable()
}
class FailOp(private val message: String) : Filter {
    override fun call(payload: Payload): Payload = throw RuntimeException(message)
}
class RecordTap(private val key: String) : Tap {
    override fun observe(payload: Payload) { taps.add(payload.get<Any?>(key)) }
}
class FailTap(private val message: String) : Tap {
    override fun observe(payload: Payload) = throw RuntimeException(message)
}
class NoopTap : Tap {
    override fun observe(payload: Payload) {}
}
/** Configurable predicates: named classes, the case's condition on the instance. */
class EqualsWhen(private val key: String, private val value: Any?) : Predicate {
    override fun test(payload: Payload) = toJson(payload.get<Any?>(key)) == toJson(value)
}
class TruthyWhen(private val key: String) : Predicate {
    override fun test(payload: Payload) = truthy(payload.get<Any?>(key))
}
/** The runner's named pipeline type: only named Pipeline subclasses nest. */
class Nested : Pipeline()

@Suppress("UNCHECKED_CAST")
fun filterFor(spec: Map<String, Any?>): Filter = when (spec["op"]) {
    "set" -> SetOp(spec.s("key"), spec["value"])
    "copy" -> CopyOp(spec.s("from"), spec.s("to"))
    "add" -> AddOp(spec.s("key"), spec["by"])
    "append" -> AppendOp(spec.s("key"), spec["value"])
    "remove" -> RemoveOp(spec.s("key"))
    "merge" -> MergeOp(spec["value"] as Map<String, Any?>)
    "has" -> HasOp(spec.s("key"), spec.s("to"))
    "mutate" -> MutateOp(spec.s("key"), spec["value"])
    "fail" -> FailOp(spec.s("message"))
    else -> throw Unsupported("unknown filter op ${spec["op"]}")
}

fun tapFor(spec: Map<String, Any?>): Tap = when (spec["op"]) {
    "record" -> RecordTap(spec.s("key"))
    "fail" -> FailTap(spec.s("message"))
    "noop" -> NoopTap()
    else -> throw Unsupported("unknown tap op ${spec["op"]}")
}

fun predicateFor(`when`: Map<String, Any?>): Predicate = when (`when`["op"]) {
    "equals" -> EqualsWhen(`when`.s("key"), `when`["value"])
    "truthy" -> TruthyWhen(`when`.s("key"))
    else -> throw Unsupported("unknown valve op ${`when`["op"]}")
}

@Suppress("UNCHECKED_CAST")
fun build(steps: List<Any?>): Pipeline = addSteps(Pipeline(), steps)

/** A nested case pipeline, as the runner's named pipeline type. */
fun buildNested(steps: List<Any?>): Nested = addSteps(Nested(), steps)

@Suppress("UNCHECKED_CAST")
fun <P : Pipeline> addSteps(p: P, steps: List<Any?>): P {
    for (raw in steps) {
        val s = raw as Map<String, Any?>
        when (s["kind"]) {
            "filter" -> p.addFilter(filterFor(s))
            "tap" -> p.addTap(tapFor(s))
            "valve" -> p.addFilter(
                Valve(filterFor(s["filter"] as Map<String, Any?>), predicateFor(s["when"] as Map<String, Any?>)))
            "pipeline" -> p.addPipeline(buildNested(s["steps"] as List<Any?>))
            else -> throw Unsupported("unknown step kind ${s["kind"]}")
        }
    }
    return p
}

object RecordHook : Hook {
    override fun before(name: String?, payload: Payload) { hooks.add("before:" to name) }
    override fun after(name: String?, payload: Payload) { hooks.add("after:" to name) }
    override fun onError(name: String?, error: Exception, payload: Payload) { hooks.add("error:" to name) }
}

@Suppress("UNCHECKED_CAST")
fun runCase(c: Map<String, Any?>): String {
    taps.clear(); hooks.clear()
    val id = c.s("id")
    val p = try { build(c["steps"] as List<Any?>) } catch (e: Unsupported) {
        return """{"id":${toJson(id)},"unsupported":${toJson(e.message)}}"""
    }
    val withHooks = c["hooks"] == true
    if (withHooks) p.useHook(RecordHook)
    val input = (c["input"] as? Map<String, Any?>) ?: emptyMap()
    val result = LinkedHashMap<String, Any?>()
    result["id"] = id
    try {
        result["output"] = p.run(Payload(input)).toDict()
    } catch (e: Exception) {
        result["error"] = "${e.javaClass.simpleName}: ${e.message}"
    }
    // Steps are identified by their class (conformance/API.md); the cases name
    // them. Each case step adds one pipeline step, in order: map identities
    // back. An identity this map does not know stays as is and fails.
    val caseSteps = c["steps"] as List<Map<String, Any?>>
    val label = p.identities.withIndex().associate { (i, id) -> id to caseSteps[i].s("name") }
    fun named(ids: List<String>) = ids.map { label[it] ?: it }
    val state = p.state
    result["state"] = mapOf(
        "executed" to named(state.executed.toList()),
        "skipped" to named(state.skipped.toList()),
        "errors" to named(state.errors.map { it.first }),
    )
    if (withHooks) result["hooks"] = hooks.map { (phase, id) -> phase + (id?.let { label[it] ?: it } ?: "") }
    result["taps"] = taps.toList()
    result["input_after"] = input
    return toJson(result)
}

object NoopHook : Hook

const val BENCH_WARMUP = 20000
const val BENCH_RUNS = 20000
const val BENCH_REPEATS = 5

/** Best of BENCH_REPEATS x BENCH_RUNS, in µs per run. */
@Suppress("UNCHECKED_CAST")
fun bench(c: Map<String, Any?>): String {
    val p = build(c["steps"] as List<Any?>)
    if (c["hooks"] == "noop") p.useHook(NoopHook)
    val input = (c["input"] as? Map<String, Any?>) ?: emptyMap()
    val output = p.run(Payload(input)).toDict()
    repeat(BENCH_WARMUP) { p.run(Payload(input)) }
    var best = Long.MAX_VALUE
    repeat(BENCH_REPEATS) {
        val t0 = System.nanoTime()
        repeat(BENCH_RUNS) { p.run(Payload(input)) }
        best = minOf(best, System.nanoTime() - t0)
    }
    val us = best.toDouble() / BENCH_RUNS / 1000.0
    return toJson(mapOf("id" to c["id"], "us_per_run" to us, "output" to output))
}

@Suppress("UNCHECKED_CAST")
fun main(args: Array<String>) {
    val cases = JsonReader(generateSequence(::readLine).joinToString("\n")).value() as List<Any?>
    val runOne: (Map<String, Any?>) -> String = if (args.firstOrNull() == "bench") ::bench else ::runCase
    println(cases.joinToString(",", "[", "]") { runOne(it as Map<String, Any?>) })
}

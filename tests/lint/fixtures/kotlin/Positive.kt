// Anonymous steps the Kotlin analyzer must flag (expect: comments name the rule).
package app

import com.codeupipe.core.*

class Named : Filter { override fun call(payload: Payload) = payload }

fun isOn(p: Payload): Boolean = true

fun makeClosure(k: String): Filter = Filter { p -> p.insert(k, 1) }

fun makePredicate(): (Payload) -> Boolean = { true }

fun makeObject(): Filter {
    return object : Filter { override fun call(payload: Payload) = payload }
}

fun makeLocal(): Filter {
    class Hidden : Filter { override fun call(payload: Payload) = payload }
    return Hidden()
}

fun filterFor(op: String): Filter = when (op) {
    "set" -> Filter { p -> p }
    else -> throw IllegalArgumentException(op)
}

fun `built in a backticked function`() {
    class Local : Filter { override fun call(payload: Payload) = payload }
    Pipeline().addFilter(Local(), "local") // expect: CUP-A003
}

fun buildChild(): Pipeline {
    return Pipeline().addFilter(Named(), "n")
}

fun build(): Pipeline {
    class Local : Filter { override fun call(payload: Payload) = payload }
    fun nestedPred(p: Payload): Boolean = true

    val p = Pipeline()
    p.addFilter(Filter { it }, "sam") // expect: CUP-A001
    p.addTap(Tap { p -> println(p) }, "tap") // expect: CUP-A001
    p.addFilter(object : Filter { override fun call(payload: Payload) = payload }, "object") // expect: CUP-A004
    p.addFilter(Local(), "local") // expect: CUP-A003
    p.addFilter(Valve("v", Named()) { true }, "trailing") // expect: CUP-A001
    p.addFilter(Valve("v", Named(), { p -> true }), "lambda") // expect: CUP-A001
    p.addFilter(Valve("v", Local(), ::isOn), "local inner") // expect: CUP-A003
    p.addFilter(Valve("v", Named(), fun(p: Payload): Boolean = true), "anonymous fun") // expect: CUP-A001
    p.addFilter(makeClosure("x"), "factory") // expect: CUP-A001
    p.addFilter(Valve("v", Named(), makePredicate()), "fn type") // expect: CUP-A001
    p.addFilter(makeObject(), "object factory") // expect: CUP-A004
    p.addFilter(makeLocal(), "local factory") // expect: CUP-A003
    p.addFilter(filterFor("set"), "when factory") // expect: CUP-A001

    val bound = Filter { it }
    p.addFilter(bound, "bound") // expect: CUP-A001
    val pred = { _: Payload -> true }
    p.addFilter(Valve("v", Named(), pred), "bound pred") // expect: CUP-A001

    val inner = Pipeline()
        .addFilter(Named(), "inner")
    p.addPipeline(inner, "inner") // expect: CUP-A005
    p.addPipeline(Pipeline(), "empty") // expect: CUP-A005
    p.addPipeline(buildChild(), "child") // expect: CUP-A005
    p.addFilter { it } // expect: CUP-A001
    val valve = Valve(
        name = "gated",
        inner = Filter { p -> p }, // expect: CUP-A001
        predicate = { p -> true } // expect: CUP-A001
    )
    p.addFilter(valve, "named arguments")
    return p
}

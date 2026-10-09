// Step-identity probe cases, with describe(label, f) replaced by
// p.addFilter(f, label): the probe's cases as lint fixtures.
package app.probe

fun interface Filter { fun call(p: Map<String, Any?>): Map<String, Any?> }

class Validate : Filter { override fun call(p: Map<String, Any?>) = p }
object Normalize : Filter { override fun call(p: Map<String, Any?>) = p }

fun makeClosure(k: String): Filter = Filter { p -> p + (k to 1) }

fun main() {
    class Local : Filter { override fun call(p: Map<String, Any?>) = p }
    val p = Pipeline()
    p.addFilter(Validate(), "class instance")
    p.addFilter(Validate(), "same class again")
    p.addFilter(Normalize, "object")
    p.addFilter(Filter { p -> p }, "SAM lambda") // expect: CUP-A001
    p.addFilter(makeClosure("x"), "returned lambda") // expect: CUP-A001
    p.addFilter(object : Filter { override fun call(p: Map<String, Any?>) = p }, "anonymous object") // expect: CUP-A004
    p.addFilter(Local(), "class defined in a function") // expect: CUP-A003
}

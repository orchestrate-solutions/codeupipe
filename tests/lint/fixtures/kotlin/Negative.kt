// Named steps the Kotlin analyzer must NOT flag.
package app

import com.codeupipe.core.*

class Named : Filter { override fun call(payload: Payload) = payload }
object Normalize : Filter { override fun call(payload: Payload) = payload }
class Audit : Tap { override fun observe(payload: Payload) {} }

class Onboarding : Pipeline() {
    init {
        addFilter(Named(), "n")
    }
}

fun isOn(p: Payload): Boolean = true
fun makeNamed(): Filter = Named()

fun build(steps: List<Filter>, pred: (Payload) -> Boolean): Pipeline {
    val text = "p.addFilter(Filter { it }, \"x\")"
    val raw = """ addFilter { it } """
    val p = Pipeline() // a plain pipeline at the top level is fine
    p.addFilter(Named(), "a")
    p.addFilter(Normalize, "object")
    p.addTap(Audit(), "audit")
    p.addFilter(Valve("v", Named(), ::isOn), "v")
    p.addFilter(Valve("v", Named(), pred), "param")
    p.addPipeline(Onboarding(), "onboarding")
    p.addFilter(makeNamed(), "factory")
    for (s in steps) p.addFilter(s, "loop")
    listOf(1, 2).map { it * 2 } // a lambda that is not a step
    println(text + raw)
    return p
}

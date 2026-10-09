// What the lexical scan cannot see (packages/codeupipe-lint/README.md). Unflagged lines are
// false negatives; an expect comment marked (false positive) is one.
package app

import com.codeupipe.core.*

class Named : Filter { override fun call(payload: Payload) = payload }
class Configured(val f: (Payload) -> Payload) : Filter { override fun call(payload: Payload) = f(payload) }

fun build(): Pipeline {
    val p = Pipeline()
    // A factory in another file: its return type is unknown here.
    p.addFilter(RemoteFactories.makeLambda(), "remote")
    // A lambda passed through a scope function.
    p.addFilter(run { Filter { it } }, "run")
    return p
}

fun wrapper(): Pipeline {
    val p = Pipeline()
    // A named class whose constructor takes a lambda, called with only a
    // trailing lambda, reads like a SAM lambda (Filter { ... }).
    p.addFilter(Configured { it }, "configured") // expect: CUP-A001 (false positive)
    return p
}

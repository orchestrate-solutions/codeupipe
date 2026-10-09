package com.codeupipe.core

/**
 * A [Valve]'s condition.
 *
 * A predicate has an identity like any step (conformance/API.md, "Step
 * identity"), and in Kotlin a lambda or even a function reference (`::isOn`)
 * compiles to a synthetic class with none. So a predicate is a named
 * `object` or class; a class carries configuration on the instance:
 *
 *     object IsVip : Predicate { override fun test(payload: Payload) = ... }
 *     class AtLeast(val n: Int) : Predicate { ... }
 */
fun interface Predicate {
    fun test(payload: Payload): Boolean
}

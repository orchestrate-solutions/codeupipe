package com.codeupipe.core

/**
 * Step identity, derived from the code (conformance/API.md, "Step identity"):
 * the qualified name of the class that runs the step. The JVM marks every
 * anonymous form (lambdas are synthetic, anonymous objects anonymous, classes
 * declared in a function local), so all of them are refused here.
 */
internal object StepIdentity {
    private const val FIX = "Declare it as a top-level class or object (a named class for a configurable " +
        "Valve predicate) so it has a stable identity and can be tested on its own."

    fun symbolOf(value: Any, what: String): String {
        val cls = value.javaClass
        val why = when {
            cls.isSynthetic || cls.name.contains("\$\$Lambda") -> "a lambda"
            cls.isAnonymousClass -> "an anonymous object"
            cls.isLocalClass -> "a class declared inside a function (${cls.simpleName})"
            else -> null
        }
        if (why != null) throw AnonymousStep("$what is $why. $FIX")
        return value::class.qualifiedName ?: throw AnonymousStep("$what (${cls.name}) has no qualified name. $FIX")
    }

    /** A step's identity before any #n occurrence number. */
    fun identify(step: Any, what: String): String =
        if (step is Valve) symbolOf(step.inner, "Filter") else symbolOf(step, what)

    /** `File.kt:line` of the code that called an add method. */
    fun addSite(): String {
        val frame = Throwable().stackTrace.firstOrNull {
            it.className != StepIdentity::class.java.name && !it.className.startsWith(Pipeline::class.java.name)
        }
        return if (frame == null) "" else "${frame.fileName}:${frame.lineNumber}"
    }
}

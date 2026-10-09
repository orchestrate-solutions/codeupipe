package com.codeupipe.core

/**
 * A step whose identity cannot be derived from the code.
 *
 * Step identity is a pointer to the filter (conformance/API.md, "Step
 * identity"). A lambda (SAM or function type), an anonymous object, a class
 * declared inside a function, or a plain [Pipeline] nested as a step has no
 * stable identity and is not independently testable, so the runtime refuses
 * it when the step is added.
 */
class AnonymousStep(message: String) : IllegalArgumentException(message)

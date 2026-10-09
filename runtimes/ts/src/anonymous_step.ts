/**
 * AnonymousStep: a step whose identity cannot be derived from the code.
 *
 * Step identity is a pointer to the filter (conformance/API.md, "Step
 * identity"). An arrow function, an object literal, a class or function
 * defined inside another function, or an unnamed nested Pipeline has no
 * stable pointer and is not independently testable, so the runtime refuses it.
 */
export class AnonymousStep extends TypeError {
  constructor(message: string) {
    super(message);
    this.name = "AnonymousStep";
  }
}

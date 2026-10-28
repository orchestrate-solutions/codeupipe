/**
 * The pipeline has a shape that the compiler does not write as plain code.
 *
 * The rule of the compiler: code that it writes behaves the same as the
 * pipeline. A shape for which it cannot keep that rule is refused, with the
 * place named and a hint that says what to do.
 */
export class CompileRefusal extends Error {
  readonly where: string;
  readonly hint: string;

  constructor(where: string, what: string, hint: string) {
    super(`${where}: ${what}. ${hint}`);
    this.name = "CompileRefusal";
    this.where = where;
    this.hint = hint;
  }
}

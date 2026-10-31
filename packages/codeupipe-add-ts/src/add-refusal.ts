/**
 * Refusal: the command cannot do what it was asked, and writes nothing.
 *
 * `exitCode` is 1 when a file exists, and 2 when the arguments cannot be used
 * (conformance/ADD.md, "What the command prints, and its exit code").
 */
export class Refusal extends Error {
  readonly exitCode: number;

  constructor(exitCode: number, message: string) {
    super(message);
    this.name = "Refusal";
    this.exitCode = exitCode;
  }
}

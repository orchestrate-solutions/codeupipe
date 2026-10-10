import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** throw an error that carries message */
export class FailFilter implements Filter {
  readonly message: string;

  constructor(message: string) {
    this.message = message;
  }

  call(_payload: Payload): Payload {
    throw new Error(this.message);
  }
}

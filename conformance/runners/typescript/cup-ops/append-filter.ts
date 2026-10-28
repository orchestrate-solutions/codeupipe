import type { Filter, Payload } from "../../../../packages/codeupipe-ts/src/index.ts";

/** insert key = a copy of get(key), or of an empty list, with value added */
export class AppendFilter implements Filter {
  readonly key: string;
  readonly value: unknown;

  constructor(key: string, value: unknown) {
    this.key = key;
    this.value = value;
  }

  call(payload: Payload): Payload {
    const list = payload.get<unknown[]>(this.key) ?? [];
    return payload.insert(this.key, [...list, this.value]);
  }
}

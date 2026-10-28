/**
 * Payload: the data that moves through a pipeline.
 *
 * One keyed container. Every write changes it in place and returns it, so a
 * step can write and return in one line. `copy()` gives a separate Payload
 * when you want to keep the one you have.
 */
export class Payload { // cup: allow-plain the framework itself: a primitive is made of this
  #data: Map<string, unknown>;
  #traceId: string | null = null;
  #lineage: string[] = [];

  /** Keys are strings; values are JSON-shaped. The map that is given is copied. */
  constructor(data?: Record<string, unknown> | null) {
    this.#data = new Map(data ? Object.entries(data) : []);
  }

  /** The value for `key`, or `fallback` when the key is absent. */
  get<T = unknown>(key: string): T | null;
  get<T>(key: string, fallback: T): T;
  get(key: string, fallback: unknown = null): unknown {
    return this.#data.has(key) ? this.#data.get(key) : fallback;
  }

  /** Whether `key` is present (also when its value is null). */
  has(key: string): boolean {
    return this.#data.has(key);
  }

  /** Set `key` to `value` in this Payload, and return it. */
  insert(key: string, value: unknown): this {
    this.#data.set(key, value);
    return this;
  }

  /** Remove `key` from this Payload (nothing happens if it is absent), and return it. */
  remove(key: string): this {
    this.#data.delete(key);
    return this;
  }

  /** Write every key of `other` into this Payload (`other` wins), and return it. */
  merge(other: Payload): this {
    for (const [key, value] of other.#data) {
      this.#data.set(key, value);
    }
    this.#traceId = this.#traceId ?? other.#traceId;
    this.#lineage.push(...other.#lineage);
    return this;
  }

  /** A separate Payload with the same contents, trace id and lineage. Values are shared. */
  copy(): Payload {
    const copy = new Payload();
    copy.#data = new Map(this.#data);
    copy.#traceId = this.#traceId;
    copy.#lineage = [...this.#lineage];
    return copy;
  }

  /** The contents as a new map. */
  toDict(): Record<string, unknown> {
    return Object.fromEntries(this.#data);
  }

  /** Set the trace id on this Payload, and return it. */
  withTrace(traceId: string): this {
    this.#traceId = traceId;
    return this;
  }

  /** The trace id, for following one Payload across systems. */
  get traceId(): string | null {
    return this.#traceId;
  }

  /** The steps this Payload has passed through, when lineage is on. */
  get lineage(): string[] {
    return [...this.#lineage];
  }

  /** Record a step in the lineage. For the Pipeline. */
  _stamp(label: string): this {
    this.#lineage.push(label);
    return this;
  }
}

/**
 * Payload: The Data Container
 *
 * Immutable data container flowing through pipelines.
 * Returns fresh copies on modification for safety.
 *
 * See also: Python, Rust, Go, C# implementations.
 */

export type PayloadData = Record<string, unknown>;

type PayloadOptions = {
  traceId?: string;
  lineage?: string[];
  _shareData?: boolean;
};

/**
 * Immutable data container — holds data flowing through the pipeline.
 * Returns fresh copies on modification for safety.
 */
export class Payload<T extends PayloadData = PayloadData> {
  private readonly _data: Readonly<T>;
  private readonly _traceId: string | undefined;
  private readonly _lineage: readonly string[];

  constructor(
    data?: T | null,
    options?: PayloadOptions,
  ) {
    this._data = data
      ? ((options?._shareData ? data : { ...data }) as T)
      : ({} as T);
    this._traceId = options?.traceId;
    this._lineage = options?.lineage ? [...options.lineage] : [];
  }

  /** Return the value for key, or default if absent. */
  // A missing key reads as null, never undefined, so a copied
  // missing value survives JSON serialisation.
  get<K extends string>(key: K, defaultValue: unknown = null): unknown {
    const val = (this._data as PayloadData)[key];
    return val !== undefined ? val : defaultValue;
  }

  /** Trace ID for distributed tracing / lineage tracking. */
  get traceId(): string | undefined {
    return this._traceId;
  }

  /** Ordered list of step names this payload has passed through. */
  get lineage(): string[] {
    return [...this._lineage];
  }

  /** Return a new Payload with trace ID set. */
  withTrace(traceId: string): Payload<T> {
    return new Payload<T>(this._data as T, {
      traceId,
      lineage: [...this._lineage],
      _shareData: true,
    });
  }

  /** Record a processing step in lineage (internal). */
  _stamp(stepName: string): Payload<T> {
    return new Payload<T>(this._data as T, {
      traceId: this._traceId,
      lineage: [...this._lineage, stepName],
      _shareData: true,
    });
  }

  /** Return a fresh Payload with the addition. */
  /** Whether the key is present (even with a null value). */
  has(key: string): boolean {
    return Object.prototype.hasOwnProperty.call(this._data, key);
  }

  /** Return a new Payload without the key (a no-op if it is absent). */
  remove(key: string): Payload<T> {
    if (!this.has(key)) return this;
    const { [key]: _removed, ...rest } = this._data as PayloadData;
    return new Payload<T>(rest as T, { traceId: this._traceId, lineage: [...this._lineage] });
  }

  insert<K extends string, V>(
    key: K,
    value: V,
  ): Payload<T & Record<K, V>> {
    const newData = { ...this._data, [key]: value } as T & Record<K, V>;
    return new Payload<T & Record<K, V>>(newData, {
      traceId: this._traceId,
      lineage: [...this._lineage],
      _shareData: true,
    });
  }

  /** Insert with type evolution — alias for insert. */
  insertAs<K extends string, V>(
    key: K,
    value: V,
  ): Payload<T & Record<K, V>> {
    return this.insert(key, value);
  }

  /** Convert to a mutable sibling for performance-critical sections. */
  withMutation(): MutablePayload<T> {
    return new MutablePayload<T>({ ...this._data } as T, {
      traceId: this._traceId,
      lineage: [...this._lineage],
      _shareData: true,
    });
  }

  /** Combine payloads, with other taking precedence on conflicts. */
  merge<U extends PayloadData>(other: Payload<U>): Payload<T & U> {
    const newData = { ...this._data, ...(other._data as U) } as T & U;
    const trace = this._traceId ?? other.traceId;
    const lineage = [...this._lineage, ...other.lineage];
    return new Payload<T & U>(newData, {
      traceId: trace,
      lineage,
      _shareData: true,
    });
  }

  /** Express as dict for ecosystem integration. */
  toDict(): T {
    return { ...this._data } as T;
  }

  /** Serialize payload for network/storage transport. */
  serialize(fmt: "json" = "json"): Uint8Array {
    if (fmt === "json") {
      const envelope: PayloadData = { data: this._data };
      if (this._traceId) envelope["trace_id"] = this._traceId;
      if (this._lineage.length > 0) envelope["lineage"] = [...this._lineage];
      return new TextEncoder().encode(JSON.stringify(envelope));
    }
    throw new Error(`Unsupported format: ${fmt}`);
  }

  /** Deserialize payload from network/storage transport. */
  static deserialize<T extends PayloadData = PayloadData>(
    raw: Uint8Array,
    fmt: "json" = "json",
  ): Payload<T> {
    if (fmt === "json") {
      const text = new TextDecoder().decode(raw);
      const envelope = JSON.parse(text) as {
        data?: T;
        trace_id?: string;
        lineage?: string[];
      };
      return new Payload<T>(envelope.data ?? ({} as T), {
        traceId: envelope.trace_id,
        lineage: envelope.lineage,
        _shareData: true,
      });
    }
    throw new Error(`Unsupported format: ${fmt}`);
  }

  toString(): string {
    if (this._traceId) {
      return `Payload(${JSON.stringify(this._data)}, traceId='${this._traceId}')`;
    }
    return `Payload(${JSON.stringify(this._data)})`;
  }
}

/**
 * Mutable data container for performance-critical sections.
 */
export class MutablePayload<T extends PayloadData = PayloadData> {
  private readonly _data: T;
  private readonly _traceId: string | undefined;
  private readonly _lineage: string[];

  constructor(
    data?: T | null,
    options?: PayloadOptions,
  ) {
    this._data = data
      ? ((options?._shareData ? data : { ...data }) as T)
      : ({} as T);
    this._traceId = options?.traceId;
    this._lineage = options?.lineage ? [...options.lineage] : [];
  }

  /** Return the value for key, or default if absent. */
  // A missing key reads as null, never undefined, so a copied
  // missing value survives JSON serialisation.
  get<K extends string>(key: K, defaultValue: unknown = null): unknown {
    const val = (this._data as PayloadData)[key];
    return val !== undefined ? val : defaultValue;
  }

  /** Change in place. */
  has(key: string): boolean {
    return Object.prototype.hasOwnProperty.call(this._data, key);
  }

  /** Remove the key in place (a no-op if it is absent). */
  remove(key: string): void {
    delete (this._data as PayloadData)[key];
  }

  set(key: string, value: unknown): void {
    (this._data as PayloadData)[key] = value;
  }

  /** Trace ID for distributed tracing / lineage tracking. */
  get traceId(): string | undefined {
    return this._traceId;
  }

  /** Ordered list of step names this payload has passed through. */
  get lineage(): string[] {
    return [...this._lineage];
  }

  /** Return to safety with a fresh immutable copy. */
  toImmutable(): Payload<T> {
    return new Payload<T>({ ...this._data } as T, {
      traceId: this._traceId,
      lineage: [...this._lineage],
      _shareData: true,
    });
  }

  toString(): string {
    return `MutablePayload(${JSON.stringify(this._data)})`;
  }
}

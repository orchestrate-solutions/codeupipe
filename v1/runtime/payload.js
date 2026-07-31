/**
 * Payload: The Data Container
 *
 * Immutable data container flowing through pipelines.
 * Returns fresh copies on modification for safety.
 *
 * Port of codeupipe/core/payload.py
 */
/**
 * Immutable data container — holds data flowing through the pipeline.
 * Returns fresh copies on modification for safety.
 */
export class Payload {
    _data;
    _traceId;
    _lineage;
    constructor(data, options) {
        this._data = data ? { ...data } : {};
        this._traceId = options?.traceId;
        this._lineage = options?.lineage ? [...options.lineage] : [];
    }
    /** Return the value for key, or default if absent. */
    get(key, defaultValue) {
        const val = this._data[key];
        return val !== undefined ? val : defaultValue;
    }
    /** Trace ID for distributed tracing / lineage tracking. */
    get traceId() {
        return this._traceId;
    }
    /** Ordered list of step names this payload has passed through. */
    get lineage() {
        return [...this._lineage];
    }
    /** Return a new Payload with trace ID set. */
    withTrace(traceId) {
        return new Payload({ ...this._data }, {
            traceId,
            lineage: [...this._lineage],
        });
    }
    /** Record a processing step in lineage (internal). */
    _stamp(stepName) {
        return new Payload({ ...this._data }, {
            traceId: this._traceId,
            lineage: [...this._lineage, stepName],
        });
    }
    /** Return a fresh Payload with the addition. */
    insert(key, value) {
        const newData = { ...this._data, [key]: value };
        return new Payload(newData, {
            traceId: this._traceId,
            lineage: [...this._lineage],
        });
    }
    /** Insert with type evolution — alias for insert. */
    insertAs(key, value) {
        return this.insert(key, value);
    }
    /** Convert to a mutable sibling for performance-critical sections. */
    withMutation() {
        return new MutablePayload({ ...this._data }, {
            traceId: this._traceId,
            lineage: [...this._lineage],
        });
    }
    /** Combine payloads, with other taking precedence on conflicts. */
    merge(other) {
        const newData = { ...this._data, ...other.toDict() };
        const trace = this._traceId ?? other.traceId;
        const lineage = [...this._lineage, ...other.lineage];
        return new Payload(newData, { traceId: trace, lineage });
    }
    /** Express as dict for ecosystem integration. */
    toDict() {
        return { ...this._data };
    }
    /** Serialize payload for network/storage transport. */
    serialize(fmt = "json") {
        if (fmt === "json") {
            const envelope = { data: this._data };
            if (this._traceId)
                envelope["trace_id"] = this._traceId;
            if (this._lineage.length > 0)
                envelope["lineage"] = [...this._lineage];
            return new TextEncoder().encode(JSON.stringify(envelope));
        }
        throw new Error(`Unsupported format: ${fmt}`);
    }
    /** Deserialize payload from network/storage transport. */
    static deserialize(raw, fmt = "json") {
        if (fmt === "json") {
            const text = new TextDecoder().decode(raw);
            const envelope = JSON.parse(text);
            return new Payload(envelope.data ?? {}, {
                traceId: envelope.trace_id,
                lineage: envelope.lineage,
            });
        }
        throw new Error(`Unsupported format: ${fmt}`);
    }
    toString() {
        if (this._traceId) {
            return `Payload(${JSON.stringify(this._data)}, traceId='${this._traceId}')`;
        }
        return `Payload(${JSON.stringify(this._data)})`;
    }
}
/**
 * Mutable data container for performance-critical sections.
 */
export class MutablePayload {
    _data;
    _traceId;
    _lineage;
    constructor(data, options) {
        this._data = data ? { ...data } : {};
        this._traceId = options?.traceId;
        this._lineage = options?.lineage ? [...options.lineage] : [];
    }
    /** Return the value for key, or default if absent. */
    get(key, defaultValue) {
        const val = this._data[key];
        return val !== undefined ? val : defaultValue;
    }
    /** Change in place. */
    set(key, value) {
        this._data[key] = value;
    }
    /** Trace ID for distributed tracing / lineage tracking. */
    get traceId() {
        return this._traceId;
    }
    /** Ordered list of step names this payload has passed through. */
    get lineage() {
        return [...this._lineage];
    }
    /** Return to safety with a fresh immutable copy. */
    toImmutable() {
        return new Payload({ ...this._data }, {
            traceId: this._traceId,
            lineage: [...this._lineage],
        });
    }
    toString() {
        return `MutablePayload(${JSON.stringify(this._data)})`;
    }
}
//# sourceMappingURL=payload.js.map
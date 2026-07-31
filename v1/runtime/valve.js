/**
 * Valve: Conditional Flow Control
 *
 * A Valve wraps a Filter with a predicate — the inner filter only
 * executes when the predicate evaluates to true. Otherwise the payload
 * passes through unchanged.
 *
 * Port of codeupipe/core/valve.py
 */
/**
 * Conditional flow control — gates a Filter with a predicate.
 *
 * Conforms to the Filter interface so it can be used anywhere a
 * Filter is expected.
 */
export class Valve {
    name;
    _inner;
    _predicate;
    /** Whether the last call was skipped. Used by Pipeline for state tracking. */
    _lastSkipped = false;
    constructor(name, inner, predicate) {
        this.name = name;
        this._inner = inner;
        this._predicate = predicate;
    }
    async call(payload) {
        if (this._predicate(payload)) {
            this._lastSkipped = false;
            return this._inner.call(payload);
        }
        this._lastSkipped = true;
        return payload;
    }
    toString() {
        return `Valve(${JSON.stringify(this.name)})`;
    }
}
//# sourceMappingURL=valve.js.map
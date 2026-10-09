package com.codeupipe.core

/**
 * Payload: The Data Container
 *
 * Immutable data container flowing through pipelines.
 * Returns fresh copies on modification for safety.
 *
 * See also: Python, TypeScript, Rust, Go, C# implementations.
 */
class Payload private constructor(
    private val data: Map<String, Any?>,
    private val _traceId: String?,
    private val _lineage: List<String>,
) {
    constructor(data: Map<String, Any?> = emptyMap()) : this(
        data = data.toMap(),
        _traceId = null,
        _lineage = emptyList(),
    )

    /** Trace ID for distributed tracing / lineage tracking. */
    val traceId: String? get() = _traceId

    /** Ordered list of step names this payload has passed through. */
    val lineage: List<String> get() = _lineage.toList()

    /**
     * Return the value for key, or default if absent. A present value of the
     * wrong type fails here, at the read (API contract), instead of coming
     * back mistyped and failing later wherever it is first used.
     */
    inline fun <reified T> get(key: String, default: T? = null): T? {
        val raw = valueFor(key) ?: return default
        return raw as? T
            ?: throw ClassCastException("value for '$key' is ${raw::class.simpleName}, not ${T::class.simpleName}")
    }

    /** Return the value for key, or throw if absent or of the wrong type. */
    inline fun <reified T> require(key: String): T {
        val raw = valueFor(key) ?: throw NoSuchElementException("Payload missing required key: $key")
        return raw as? T
            ?: throw ClassCastException("value for '$key' is ${raw::class.simpleName}, not ${T::class.simpleName}")
    }

    @PublishedApi internal fun valueFor(key: String): Any? = data[key]

    /** Check if key is present. */
    fun has(key: String): Boolean = data.containsKey(key)

    /** Return a fresh Payload with the addition. */
    fun insert(key: String, value: Any?): Payload {
        val newData = data.toMutableMap()
        newData[key] = value
        return Payload(newData, _traceId, _lineage.toList())
    }

    /** Return a new Payload without the key (a no-op if it is absent). */
    fun remove(key: String): Payload {
        if (!data.containsKey(key)) return this
        return Payload(data - key, _traceId, _lineage.toList())
    }

    /** Insert with type evolution — alias for insert. */
    fun insertAs(key: String, value: Any?): Payload = insert(key, value)

    /** Return a new Payload with trace ID set. */
    fun withTrace(traceId: String): Payload {
        return Payload(data.toMap(), traceId, _lineage.toList())
    }

    /** Record a processing step in lineage (internal). */
    internal fun stamp(stepName: String): Payload {
        return Payload(data.toMap(), _traceId, _lineage + stepName)
    }

    /** Combine payloads, with other taking precedence on conflicts. */
    fun merge(other: Payload): Payload {
        val merged = data.toMutableMap()
        merged.putAll(other.data)
        val trace = _traceId ?: other._traceId
        val mergedLineage = _lineage + other._lineage
        return Payload(merged, trace, mergedLineage)
    }

    /** Convert to a mutable sibling for performance-critical sections. */
    fun withMutation(): MutablePayload {
        return MutablePayload(data.toMutableMap(), _traceId, _lineage.toMutableList())
    }

    /** Express as dict for ecosystem integration. */
    fun toDict(): Map<String, Any?> = data.toMap()

    /** Number of entries. */
    val size: Int get() = data.size

    /** All keys. */
    val keys: Set<String> get() = data.keys.toSet()

    override fun toString(): String = "Payload($data)"

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Payload) return false
        return data == other.data
    }

    override fun hashCode(): Int = data.hashCode()
}

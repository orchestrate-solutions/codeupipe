package com.codeupipe.core

/**
 * MutablePayload: Bulk Edit Sibling
 *
 * Mutable version of Payload for when you need many in-place edits.
 * Convert to immutable with [toImmutable].
 */
class MutablePayload internal constructor(
    private val data: MutableMap<String, Any?>,
    private var _traceId: String?,
    private val _lineage: MutableList<String>,
) {
    constructor(data: MutableMap<String, Any?> = mutableMapOf()) : this(
        data = data,
        _traceId = null,
        _lineage = mutableListOf(),
    )

    /** Set a value. Returns this for chaining. */
    fun set(key: String, value: Any?): MutablePayload {
        data[key] = value
        return this
    }

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

    @PublishedApi internal fun valueFor(key: String): Any? = data[key]

    /** Check if key is present. */
    fun has(key: String): Boolean = data.containsKey(key)

    /** Remove a key. */
    fun remove(key: String): MutablePayload {
        data.remove(key)
        return this
    }

    /** Freeze into an immutable Payload. */
    fun toImmutable(): Payload {
        return Payload(data.toMap()).let { p ->
            var result = p
            _traceId?.let { result = result.withTrace(it) }
            _lineage.forEach { result = result.stamp(it) }
            result
        }
    }

    /** Express as dict. */
    fun toDict(): Map<String, Any?> = data.toMap()

    /** Number of entries. */
    val size: Int get() = data.size
}

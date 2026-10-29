package codeupipe

import "maps"

// Payload is the data that moves through a pipeline.
//
// One keyed container. Keys are strings, and values are JSON-shaped, in the
// shapes that encoding/json gives: nil, bool, float64, string, []any and
// map[string]any. Every write changes the Payload in place and returns it,
// so writes chain. Copy gives a separate Payload when you want to keep the
// one you have.
//
// The zero Payload is empty and ready to use.
type Payload struct {
	data    map[string]any
	traceID string
	lineage []string
}

// NewPayload gives a Payload with the keys of data. The map is copied, so
// the Payload does not change it. It can be nil.
func NewPayload(data map[string]any) *Payload {
	payload := &Payload{data: make(map[string]any, len(data))}
	for key, value := range data {
		payload.data[key] = number(value)
	}
	return payload
}

// Get gives the value of key, or nil when key is absent. A default is a type
// assertion: price, ok := payload.Get("price").(float64).
func (p *Payload) Get(key string) any {
	return p.data[key]
}

// Has tells whether key is present, also when its value is nil.
func (p *Payload) Has(key string) bool {
	_, ok := p.data[key]
	return ok
}

// Insert sets key to value in this Payload, and returns it. A number of
// another Go type (int, int64, float32 and the others) is kept as a float64.
func (p *Payload) Insert(key string, value any) *Payload {
	if p.data == nil {
		p.data = make(map[string]any)
	}
	p.data[key] = number(value)
	return p
}

// Remove removes key from this Payload (nothing happens if it is absent),
// and returns it.
func (p *Payload) Remove(key string) *Payload {
	delete(p.data, key)
	return p
}

// Merge writes every key of other into this Payload (other wins), and
// returns it. It keeps its trace id, or takes the trace id of other when it
// has none, and adds the lineage of other to its own.
func (p *Payload) Merge(other *Payload) *Payload {
	if p.data == nil {
		p.data = make(map[string]any, len(other.data))
	}
	for key, value := range other.data {
		p.data[key] = value
	}
	if p.traceID == "" {
		p.traceID = other.traceID
	}
	p.lineage = append(p.lineage, other.lineage...)
	return p
}

// Copy gives a separate Payload with the same contents, trace id and
// lineage. The copy is shallow: the two Payloads have separate keys and
// share their values. Copy a nested list or map before you change it.
func (p *Payload) Copy() *Payload {
	data := maps.Clone(p.data)
	if data == nil {
		data = make(map[string]any)
	}
	return &Payload{data: data, traceID: p.traceID, lineage: append([]string(nil), p.lineage...)}
}

// ToDict gives the contents as a new map.
func (p *Payload) ToDict() map[string]any {
	if p.data == nil {
		return map[string]any{}
	}
	return maps.Clone(p.data)
}

// WithTrace sets the trace id on this Payload, and returns it.
func (p *Payload) WithTrace(traceID string) *Payload {
	p.traceID = traceID
	return p
}

// TraceID gives the trace id, for following one Payload across systems. It
// is "" until it is set.
func (p *Payload) TraceID() string {
	return p.traceID
}

// Lineage gives the labels of the steps that this Payload has passed
// through, when lineage is on (Pipeline.Observe).
func (p *Payload) Lineage() []string {
	return append([]string{}, p.lineage...)
}

// Stamp records a step in the lineage. The Pipeline calls it.
func (p *Payload) Stamp(label string) {
	p.lineage = append(p.lineage, label)
}

// number gives a number of any Go type as a float64, the one number type of
// a Payload, and any other value as it is.
func number(value any) any {
	switch n := value.(type) {
	case int:
		return float64(n)
	case int8:
		return float64(n)
	case int16:
		return float64(n)
	case int32:
		return float64(n)
	case int64:
		return float64(n)
	case uint:
		return float64(n)
	case uint8:
		return float64(n)
	case uint16:
		return float64(n)
	case uint32:
		return float64(n)
	case uint64:
		return float64(n)
	case uintptr:
		return float64(n)
	case float32:
		return float64(n)
	}
	return value
}

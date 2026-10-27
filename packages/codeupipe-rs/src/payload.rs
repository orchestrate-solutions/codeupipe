use crate::map::Map;
use crate::value::Value;

/// Payload: the data that moves through a pipeline.
///
/// One keyed container. Every write changes it in place and returns it, so
/// writes can be chained. `copy()` gives a separate Payload when you want to
/// keep the one you have.
#[derive(Debug, Default)]
pub struct Payload {
    data: Map,
    trace_id: Option<String>,
    lineage: Vec<String>,
}

impl Payload {
    /// An empty Payload.
    pub fn new() -> Self {
        Payload::default()
    }

    /// A Payload with the contents of `data`. The map is moved in, so the
    /// caller's map cannot be changed through the Payload.
    pub fn from_map(data: Map) -> Self {
        Payload {
            data,
            ..Payload::default()
        }
    }

    /// The value for `key`, or absent. A default is `.unwrap_or(...)`.
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.data.get(key)
    }

    /// Whether `key` is present (also when its value is null).
    pub fn has(&self, key: &str) -> bool {
        self.data.contains_key(key)
    }

    /// Set `key` to `value` in this Payload, and return it.
    pub fn insert<K: AsRef<str> + Into<String>>(
        &mut self,
        key: K,
        value: impl Into<Value>,
    ) -> &mut Self {
        self.data.insert(key, value);
        self
    }

    /// Remove `key` from this Payload (nothing happens if it is absent), and return it.
    pub fn remove(&mut self, key: &str) -> &mut Self {
        self.data.remove(key);
        self
    }

    /// Write every key of `other` into this Payload (`other` wins), and return it.
    pub fn merge(&mut self, other: &Payload) -> &mut Self {
        for (key, value) in other.data.iter() {
            self.data.insert(key, value.clone());
        }
        if self.trace_id.is_none() {
            self.trace_id = other.trace_id.clone();
        }
        self.lineage.extend(other.lineage.iter().cloned());
        self
    }

    /// A separate Payload with the same contents, trace id and lineage.
    pub fn copy(&self) -> Payload {
        Payload {
            data: self.data.clone(),
            trace_id: self.trace_id.clone(),
            lineage: self.lineage.clone(),
        }
    }

    /// The contents as a new map.
    pub fn to_dict(&self) -> Map {
        self.data.clone()
    }

    /// Set the trace id on this Payload, and return it.
    pub fn with_trace(&mut self, trace_id: impl Into<String>) -> &mut Self {
        self.trace_id = Some(trace_id.into());
        self
    }

    /// The trace id, for following one Payload across systems.
    pub fn trace_id(&self) -> Option<&str> {
        self.trace_id.as_deref()
    }

    /// The steps this Payload has passed through, when lineage is on.
    pub fn lineage(&self) -> &[String] {
        &self.lineage
    }

    /// Record a step in the lineage. For the Pipeline.
    pub(crate) fn stamp(&mut self, label: &str) {
        self.lineage.push(label.to_string());
    }
}

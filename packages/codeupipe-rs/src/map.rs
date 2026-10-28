use std::collections::HashMap;
use std::fmt;
use std::sync::Arc;

use crate::value::Value;

/// A map with more keys than this has an index; a smaller one is searched in
/// order, which is faster than hashing for a few keys.
const INDEX_FROM: usize = 8;

/// A map from text keys to values. Keys keep the order in which they were
/// first inserted, as a Python dict and a JavaScript Map do.
///
/// Two maps are equal when they have the same entries, in any order, as two
/// JSON objects are.
#[derive(Clone, Default)]
pub struct Map {
    // A key is made once and shared, by the index and by a clone of the map.
    entries: Vec<(Arc<str>, Value)>,
    index: Option<HashMap<Arc<str>, usize>>,
}

// cup: allow-plain a primitive itself: the framework makes the primitives, so it is not written with them
impl Map {
    pub fn new() -> Self {
        Map::default()
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    fn position(&self, key: &str) -> Option<usize> {
        match &self.index {
            Some(index) => index.get(key).copied(),
            None => self.entries.iter().position(|(known, _)| &**known == key),
        }
    }

    pub fn contains_key(&self, key: &str) -> bool {
        self.position(key).is_some()
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.position(key).map(|at| &self.entries[at].1)
    }

    /// Set `key` to `value`. A key that is there keeps its place.
    pub fn insert(&mut self, key: impl AsRef<str>, value: impl Into<Value>) {
        let value = value.into();
        let key = key.as_ref();
        if let Some(at) = self.position(key) {
            self.entries[at].1 = value;
            return;
        }
        let key: Arc<str> = Arc::from(key);
        let at = self.entries.len();
        self.entries.push((Arc::clone(&key), value));
        match &mut self.index {
            Some(index) => {
                index.insert(key, at);
            }
            None if self.entries.len() > INDEX_FROM => {
                // Room for a few times the size, so that a map that is filled
                // key by key does not grow its index at every doubling.
                let mut index = HashMap::with_capacity(4 * INDEX_FROM);
                for (at, (key, _)) in self.entries.iter().enumerate() {
                    index.insert(Arc::clone(key), at);
                }
                self.index = Some(index);
            }
            None => {}
        }
    }

    /// Remove `key`, and give its value. Nothing happens if it is absent.
    pub fn remove(&mut self, key: &str) -> Option<Value> {
        let at = self.position(key)?;
        let (_, value) = self.entries.remove(at);
        if let Some(index) = &mut self.index {
            index.remove(key);
            for (moved, (key, _)) in self.entries.iter().enumerate().skip(at) {
                index.insert(Arc::clone(key), moved);
            }
        }
        Some(value)
    }

    pub fn keys(&self) -> impl Iterator<Item = &str> {
        self.entries.iter().map(|(key, _)| &**key)
    }

    pub fn iter(&self) -> impl Iterator<Item = (&str, &Value)> {
        self.entries.iter().map(|(key, value)| (&**key, value))
    }
}

impl PartialEq for Map {
    fn eq(&self, other: &Self) -> bool {
        self.len() == other.len()
            && self
                .iter()
                .all(|(key, value)| other.get(key) == Some(value))
    }
}

impl fmt::Debug for Map {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_map().entries(self.iter()).finish()
    }
}

// cup: allow-plain a primitive itself: the framework makes the primitives, so it is not written with them
impl<K: AsRef<str>, V: Into<Value>> FromIterator<(K, V)> for Map {
    fn from_iter<I: IntoIterator<Item = (K, V)>>(entries: I) -> Self {
        let mut map = Map::new();
        for (key, value) in entries {
            map.insert(key, value);
        }
        map
    }
}

impl<K: AsRef<str>, V: Into<Value>, const N: usize> From<[(K, V); N]> for Map {
    fn from(entries: [(K, V); N]) -> Self {
        entries.into_iter().collect()
    }
}

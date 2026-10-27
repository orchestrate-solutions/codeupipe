use std::collections::HashMap;
use std::fmt;

use crate::value::Value;

/// A map from text keys to values. Keys keep the order in which they were
/// first inserted, as a Python dict and a JavaScript Map do.
///
/// Two maps are equal when they have the same entries, in any order, as two
/// JSON objects are.
#[derive(Clone, Default)]
pub struct Map {
    entries: Vec<(String, Value)>,
    index: HashMap<String, usize>,
}

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

    pub fn contains_key(&self, key: &str) -> bool {
        self.index.contains_key(key)
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.index.get(key).map(|&at| &self.entries[at].1)
    }

    /// Set `key` to `value`. A key that is there keeps its place.
    pub fn insert(&mut self, key: impl Into<String>, value: impl Into<Value>) {
        let key = key.into();
        let value = value.into();
        match self.index.get(&key) {
            Some(&at) => self.entries[at].1 = value,
            None => {
                self.index.insert(key.clone(), self.entries.len());
                self.entries.push((key, value));
            }
        }
    }

    /// Remove `key`, and give its value. Nothing happens if it is absent.
    pub fn remove(&mut self, key: &str) -> Option<Value> {
        let at = self.index.remove(key)?;
        let (_, value) = self.entries.remove(at);
        for (moved, (key, _)) in self.entries.iter().enumerate().skip(at) {
            if let Some(slot) = self.index.get_mut(key) {
                *slot = moved;
            }
        }
        Some(value)
    }

    pub fn keys(&self) -> impl Iterator<Item = &str> {
        self.entries.iter().map(|(key, _)| key.as_str())
    }

    pub fn iter(&self) -> impl Iterator<Item = (&str, &Value)> {
        self.entries
            .iter()
            .map(|(key, value)| (key.as_str(), value))
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

impl<K: Into<String>, V: Into<Value>> FromIterator<(K, V)> for Map {
    fn from_iter<I: IntoIterator<Item = (K, V)>>(entries: I) -> Self {
        let mut map = Map::new();
        for (key, value) in entries {
            map.insert(key, value);
        }
        map
    }
}

impl<K: Into<String>, V: Into<Value>, const N: usize> From<[(K, V); N]> for Map {
    fn from(entries: [(K, V); N]) -> Self {
        entries.into_iter().collect()
    }
}

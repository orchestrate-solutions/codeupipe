use std::collections::hash_map::RandomState;
use std::collections::HashMap;
use std::fmt;
use std::hash::{BuildHasher, BuildHasherDefault, Hasher};
use std::sync::{Arc, OnceLock};

use crate::value::Value;

/// A map with more keys than this has an index; a smaller one is searched in
/// order, which is faster than hashing for a few keys.
const INDEX_FROM: usize = 8;

/// The hash of a key, with keys that are random for each process, so that
/// keys from outside cannot be chosen to have the same hash.
fn hash_of(key: &str) -> u64 {
    static STATE: OnceLock<RandomState> = OnceLock::new();
    STATE.get_or_init(RandomState::new).hash_one(key)
}

/// The index is keyed by the hash of a key, which is mixed already: it is not
/// hashed a second time.
#[derive(Clone, Copy, Default)]
struct HashIsTheKey(u64);

impl Hasher for HashIsTheKey {
    fn finish(&self) -> u64 {
        self.0
    }

    fn write(&mut self, _bytes: &[u8]) {
        unreachable!("the index is keyed by a u64");
    }

    fn write_u64(&mut self, hash: u64) {
        self.0 = hash;
    }
}

/// A key of this many bytes or fewer is kept in the entry itself, with no
/// allocation: most keys are short (`price`, `qty`). The key then takes 24
/// bytes, as a shared one does.
const INLINE: usize = 22;

/// A key: its bytes in the entry, or a text that a clone of the map shares.
#[derive(Clone)]
enum Key {
    Inline { len: u8, bytes: [u8; INLINE] },
    Shared(Arc<str>),
}

// cup: allow-plain a part of a primitive itself: the framework makes the primitives, so it is not written with them
impl Key {
    fn new(key: &str) -> Key {
        if key.len() > INLINE {
            return Key::Shared(Arc::from(key));
        }
        let mut bytes = [0; INLINE];
        bytes[..key.len()].copy_from_slice(key.as_bytes());
        Key::Inline {
            len: key.len() as u8,
            bytes,
        }
    }

    fn bytes(&self) -> &[u8] {
        match self {
            Key::Inline { len, bytes } => &bytes[..*len as usize],
            Key::Shared(text) => text.as_bytes(),
        }
    }

    fn is(&self, key: &str) -> bool {
        self.bytes() == key.as_bytes()
    }

    fn as_str(&self) -> &str {
        match self {
            // The bytes are those of a whole str, so they are text.
            Key::Inline { .. } => std::str::from_utf8(self.bytes()).expect("a key is text"),
            Key::Shared(text) => text,
        }
    }
}

/// The hash of each key to its place. Two keys with one hash have one place
/// here: the search then goes in order, so it is right in each case.
type Index = HashMap<u64, usize, BuildHasherDefault<HashIsTheKey>>;

/// A map from text keys to values. Keys keep the order in which they were
/// first inserted, as a Python dict and a JavaScript Map do.
///
/// Two maps are equal when they have the same entries, in any order, as two
/// JSON objects are.
#[derive(Clone, Default)]
pub struct Map {
    entries: Vec<(Key, Value)>,
    index: Option<Index>,
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

    fn scan(&self, key: &str) -> Option<usize> {
        self.entries.iter().position(|(known, _)| known.is(key))
    }

    /// The place of `key` through the index, with `hash`, the hash of `key`.
    fn find_indexed(&self, index: &Index, key: &str, hash: u64) -> Option<usize> {
        match index.get(&hash) {
            None => None,
            Some(&at) if self.entries[at].0.is(key) => Some(at),
            // Another key with the same hash has this place.
            Some(_) => self.scan(key),
        }
    }

    fn position(&self, key: &str) -> Option<usize> {
        match &self.index {
            None => self.scan(key),
            Some(index) => self.find_indexed(index, key, hash_of(key)),
        }
    }

    fn build_index(&mut self) {
        // Room for a few times the size, so that a map that is filled
        // key by key does not grow its index at every doubling.
        let mut index = Index::with_capacity_and_hasher(4 * self.entries.len(), Default::default());
        for (at, (key, _)) in self.entries.iter().enumerate() {
            index.insert(hash_of(key.as_str()), at);
        }
        self.index = Some(index);
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
        let Some(index) = &self.index else {
            // A small map: searched in order, with no hash.
            match self.scan(key) {
                Some(at) => self.entries[at].1 = value,
                None => {
                    self.entries.push((Key::new(key), value));
                    if self.entries.len() > INDEX_FROM {
                        self.build_index();
                    }
                }
            }
            return;
        };
        // One hash for the search and for the index.
        let hash = hash_of(key);
        if let Some(at) = self.find_indexed(index, key, hash) {
            self.entries[at].1 = value;
            return;
        }
        let at = self.entries.len();
        self.entries.push((Key::new(key), value));
        if let Some(index) = &mut self.index {
            index.insert(hash, at);
        }
    }

    /// Remove `key`, and give its value. Nothing happens if it is absent.
    pub fn remove(&mut self, key: &str) -> Option<Value> {
        let at = self.position(key)?;
        let (_, value) = self.entries.remove(at);
        // Each key after it has a new place, and two keys can share a hash:
        // the index is made again. A remove is rare.
        if self.index.is_some() {
            self.build_index();
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

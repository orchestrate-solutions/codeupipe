use crate::key_type::KeyType;
use crate::place::Place;

/// How a step uses a key: a read or a write with a type, or a use with no
/// type (`has`, `remove`, a write of an expression).
#[derive(Clone, Debug)]
pub struct KeyUse {
    pub key: String,
    /// The type that this use gives the key, when it gives one.
    pub key_type: Option<KeyType>,
    /// A write of a value whose type the compiler cannot tell.
    pub untyped_write: bool,
    pub step: String,
    pub place: Place,
}

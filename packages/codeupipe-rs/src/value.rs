use std::fmt;

use crate::map::Map;

/// A JSON-shaped value: what a Payload holds under a key.
///
/// There is one number type, as in JSON and JavaScript: `1` and `1.0` are
/// the same value. `true` is never `1`.
#[derive(Clone, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Number(f64),
    String(String),
    List(Vec<Value>),
    Map(Map),
}

impl Value {
    pub fn is_null(&self) -> bool {
        matches!(self, Value::Null)
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Value::Bool(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Value::Number(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::String(value) => Some(value),
            _ => None,
        }
    }

    pub fn as_list(&self) -> Option<&[Value]> {
        match self {
            Value::List(value) => Some(value),
            _ => None,
        }
    }

    pub fn as_map(&self) -> Option<&Map> {
        match self {
            Value::Map(value) => Some(value),
            _ => None,
        }
    }
}

/// Written as JSON is, so that a printed Payload reads like the data.
impl fmt::Debug for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Null => f.write_str("null"),
            Value::Bool(value) => write!(f, "{value}"),
            Value::Number(value) if value.fract() == 0.0 && value.abs() < 1e15 => {
                write!(f, "{}", *value as i64)
            }
            Value::Number(value) => write!(f, "{value}"),
            Value::String(value) => write!(f, "{value:?}"),
            Value::List(values) => f.debug_list().entries(values).finish(),
            Value::Map(map) => write!(f, "{map:?}"),
        }
    }
}

impl From<bool> for Value {
    fn from(value: bool) -> Self {
        Value::Bool(value)
    }
}

macro_rules! number_from {
    ($($t:ty),*) => {
        $(impl From<$t> for Value {
            fn from(value: $t) -> Self {
                Value::Number(value as f64)
            }
        })*
    };
}

number_from!(f64, f32, i8, i16, i32, i64, isize, u8, u16, u32, u64, usize);

impl From<&str> for Value {
    fn from(value: &str) -> Self {
        Value::String(value.to_string())
    }
}

impl From<String> for Value {
    fn from(value: String) -> Self {
        Value::String(value)
    }
}

impl From<Vec<Value>> for Value {
    fn from(value: Vec<Value>) -> Self {
        Value::List(value)
    }
}

impl From<Map> for Value {
    fn from(value: Map) -> Self {
        Value::Map(value)
    }
}

impl<T: Into<Value>> From<Option<T>> for Value {
    fn from(value: Option<T>) -> Self {
        value.map_or(Value::Null, Into::into)
    }
}

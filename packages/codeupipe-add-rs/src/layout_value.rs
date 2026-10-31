/// A value of a layout file, as the YAML reader gives it.
///
/// The command needs only mappings, lists and texts. A mapping keeps the
/// order of its keys, so a message names them in the order of the file. Any
/// other value (a number, a boolean, null) is `Other`, with its text for a
/// message: no key of the contract takes one.
#[derive(Clone, Debug, PartialEq)]
pub enum LayoutValue {
    Map(Vec<(String, LayoutValue)>),
    List(Vec<LayoutValue>),
    Text(String),
    Other(String),
}

// cup: allow-plain the reading of a value of the file: data access for the steps, not a step
impl LayoutValue {
    /// The value of `key` in a mapping, or `None`.
    pub fn get(&self, key: &str) -> Option<&LayoutValue> {
        match self {
            LayoutValue::Map(pairs) => pairs
                .iter()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value),
            _ => None,
        }
    }

    /// The text of a `Text`, or `None`.
    pub fn as_text(&self) -> Option<&str> {
        match self {
            LayoutValue::Text(text) => Some(text),
            _ => None,
        }
    }

    /// The value as a message shows it: `"Discount"`, `[a, b]`, `{valve: [a]}`.
    pub fn shown(&self) -> String {
        match self {
            LayoutValue::Map(pairs) => {
                let inner: Vec<String> = pairs
                    .iter()
                    .map(|(key, value)| format!("{key}: {}", value.shown()))
                    .collect();
                format!("{{{}}}", inner.join(", "))
            }
            LayoutValue::List(items) => {
                let inner: Vec<String> = items.iter().map(LayoutValue::shown).collect();
                format!("[{}]", inner.join(", "))
            }
            LayoutValue::Text(text) => format!("{text:?}"),
            LayoutValue::Other(text) => text.clone(),
        }
    }
}

use codeupipe::{Filter, Payload, StepError, Value};

/// Writes a note and a badge for a VIP. A note that the caller gave is
/// written over.
pub struct NoteFilter;

impl Filter for NoteFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let name = payload.get("name").and_then(Value::as_str).unwrap_or("");
        payload.insert("note", format!("VIP guest {name}"));
        payload.insert("badge", "gold");
        Ok(())
    }
}

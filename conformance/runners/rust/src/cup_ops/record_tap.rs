use codeupipe::{Payload, StepError, Tap, Value};

use super::sink;

/// append get(key) to the runner's tap log
pub struct RecordTap {
    pub key: String,
}

impl Tap for RecordTap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        sink::record(payload.get(&self.key).cloned().unwrap_or(Value::Null));
        Ok(())
    }
}

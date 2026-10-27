use std::cell::RefCell;
use std::rc::Rc;

use codeupipe::{Hook, Payload, StepError};

/// Records before:<step>, after:<step> and error:<step>. Events of the
/// pipeline itself have an empty step.
pub struct RecordHook {
    pub events: Rc<RefCell<Vec<String>>>,
}

impl RecordHook {
    fn record(&self, event: &str, step: Option<&str>) {
        self.events
            .borrow_mut()
            .push(format!("{event}:{}", step.unwrap_or("")));
    }
}

impl Hook for RecordHook {
    fn before(&self, step: Option<&str>, _payload: &Payload) {
        self.record("before", step);
    }

    fn after(&self, step: Option<&str>, _payload: &Payload) {
        self.record("after", step);
    }

    fn on_error(&self, step: Option<&str>, _error: &StepError, _payload: &Payload) {
        self.record("error", step);
    }
}

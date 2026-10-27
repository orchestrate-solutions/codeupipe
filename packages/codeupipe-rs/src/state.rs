use std::fmt;
use std::time::Duration;

use crate::step_error::StepError;

/// State: what happened in the last run.
///
/// Which steps executed, which a Valve skipped, the errors, and the timings
/// when timing is on. Read it after a run through `pipeline.state()`.
#[derive(Debug, Default)]
pub struct State {
    executed: Labels,
    skipped: Labels,
    errors: Vec<(String, StepError)>,
    timings: Vec<(String, Duration)>,
}

/// A list of labels whose Strings are kept from one run to the next and
/// written over, so that a run like the last one makes no new String.
#[derive(Default)]
struct Labels {
    all: Vec<String>,
    len: usize,
}

impl Labels {
    fn push(&mut self, label: &str) {
        match self.all.get_mut(self.len) {
            Some(slot) => {
                slot.clear();
                slot.push_str(label);
            }
            None => self.all.push(label.to_string()),
        }
        self.len += 1;
    }

    fn as_slice(&self) -> &[String] {
        &self.all[..self.len]
    }

    fn clear(&mut self) {
        self.len = 0;
    }
}

impl fmt::Debug for Labels {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_list().entries(self.as_slice()).finish()
    }
}

impl State {
    /// Step labels, in order.
    pub fn executed(&self) -> &[String] {
        self.executed.as_slice()
    }

    /// Steps that a Valve did not run.
    pub fn skipped(&self) -> &[String] {
        self.skipped.as_slice()
    }

    /// Pairs of label and error.
    pub fn errors(&self) -> &[(String, StepError)] {
        &self.errors
    }

    /// Label and time, in order, when timing is on.
    pub fn timings(&self) -> &[(String, Duration)] {
        &self.timings
    }

    /// Empty, for a new run. The storage is kept.
    pub(crate) fn reset(&mut self) {
        self.executed.clear();
        self.skipped.clear();
        self.errors.clear();
        self.timings.clear();
    }

    pub(crate) fn mark_executed(&mut self, label: &str) {
        self.executed.push(label);
    }

    pub(crate) fn mark_skipped(&mut self, label: &str) {
        self.skipped.push(label);
    }

    pub(crate) fn record_error(&mut self, label: &str, error: StepError) {
        self.errors.push((label.to_string(), error));
    }

    pub(crate) fn record_timing(&mut self, label: &str, time: Duration) {
        match self.timings.iter_mut().find(|(known, _)| known == label) {
            Some(entry) => entry.1 = time,
            None => self.timings.push((label.to_string(), time)),
        }
    }
}

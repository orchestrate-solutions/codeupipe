use std::time::Duration;

use crate::step_error::StepError;

/// State: what happened in the last run.
///
/// Which steps executed, which a Valve skipped, the errors, and the timings
/// when timing is on. Read it after a run through `pipeline.state()`.
#[derive(Debug, Default)]
pub struct State {
    executed: Vec<String>,
    skipped: Vec<String>,
    errors: Vec<(String, StepError)>,
    timings: Vec<(String, Duration)>,
}

impl State {
    /// Step labels, in order.
    pub fn executed(&self) -> &[String] {
        &self.executed
    }

    /// Steps that a Valve did not run.
    pub fn skipped(&self) -> &[String] {
        &self.skipped
    }

    /// Pairs of label and error.
    pub fn errors(&self) -> &[(String, StepError)] {
        &self.errors
    }

    /// Label and time, in order, when timing is on.
    pub fn timings(&self) -> &[(String, Duration)] {
        &self.timings
    }

    pub(crate) fn mark_executed(&mut self, label: &str) {
        self.executed.push(label.to_string());
    }

    pub(crate) fn mark_skipped(&mut self, label: &str) {
        self.skipped.push(label.to_string());
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

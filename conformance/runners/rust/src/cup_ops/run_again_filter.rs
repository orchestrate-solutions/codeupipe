use codeupipe::{Filter, Map, Payload, StepError, Value};

use super::sink;

/// when get("inner") is not true: run the pipeline that this step is in one
/// more time, with `input` and a new State. How a pipeline is run again
/// depends on the target, so the runner gives that as a function
/// (`sink::run_again`). Then the payload goes on with no change.
pub struct RunAgainFilter {
    pub input: Map,
}

impl Filter for RunAgainFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        if payload.get("inner") != Some(&Value::Bool(true)) {
            sink::run_again(self.input.clone())?;
        }
        Ok(())
    }
}

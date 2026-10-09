//! On a failure, `on_error` fires for the failing step and then for the
//! pipeline (`None`), mirroring before/after, which fire at both levels.
//! Same contract in every runtime: conformance/cases/hook.json.
use std::sync::{Arc, Mutex};

use codeupipe_core::{Filter, Hook, Parallel, Payload, Pipeline, Value};

type BoxError = Box<dyn std::error::Error + Send + Sync>;

struct Record(Arc<Mutex<Vec<String>>>);

impl Hook for Record {
    fn before(&self, step: Option<&str>, _: &Payload) {
        self.0.lock().unwrap().push(format!("before:{}", step.unwrap_or("")));
    }
    fn after(&self, step: Option<&str>, _: &Payload) {
        self.0.lock().unwrap().push(format!("after:{}", step.unwrap_or("")));
    }
    fn on_error(&self, step: Option<&str>, _: &(dyn std::error::Error + Send + Sync), _: &Payload) {
        self.0.lock().unwrap().push(format!("error:{}", step.unwrap_or("")));
    }
}

struct Set;
impl Filter for Set {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        Ok(p.insert("a", Value::Int(1)))
    }
}

struct Boom;
impl Filter for Boom {
    fn call(&self, _: Payload) -> Result<Payload, BoxError> {
        Err("boom".into())
    }
}

fn recorded(build: impl FnOnce(Pipeline) -> Pipeline) -> Vec<String> {
    let calls = Arc::new(Mutex::new(Vec::new()));
    let mut p = build(Pipeline::new()).use_hook(Box::new(Record(calls.clone())));
    assert!(p.run(Payload::new()).is_err());
    let out = calls.lock().unwrap().clone();
    out
}

#[test]
fn a_failing_filter_fires_on_error_for_the_step_then_the_pipeline() {
    let calls = recorded(|p| p.add_filter(Set).add_filter(Boom));

    let (a, b) = ("on_error::Set", "on_error::Boom");
    assert_eq!(
        calls,
        ["before:".to_string(), format!("before:{a}"), format!("after:{a}"), format!("before:{b}"),
            format!("error:{b}"), "error:".to_string()]
    );
}

#[test]
fn a_failing_parallel_group_fires_on_error_for_the_group_then_the_pipeline() {
    let calls = recorded(|p| p.add_parallel(Parallel::new().with(Set).with(Boom)));

    assert_eq!(calls, ["before:", "error:parallel[on_error::Set,on_error::Boom]", "error:"]);
}

//! Rust conformance runner: executes cases, reports what happened.
//!
//!     cargo run --release < cases.json > results.json
//!
//! Mirrors conformance/runners/python/runner.py; conformance/run.py judges.
//! Rust Taps fail by panicking (`observe` returns nothing); a panic that
//! escapes the pipeline is caught here and reported as the run's error.
use std::collections::HashMap;
use std::io::Read;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::sync::Mutex;

use codeupipe_core::{Filter, Hook, Nestable, Payload, Pipeline, Predicate, Tap, Valve, Value};
use serde_json::{json, Map, Value as Json};

static TAPS: Mutex<Vec<Json>> = Mutex::new(Vec::new());
static HOOKS: Mutex<Vec<String>> = Mutex::new(Vec::new());

type BoxError = Box<dyn std::error::Error + Send + Sync>;

fn to_value(j: &Json) -> Value {
    match j {
        Json::Null => Value::Null,
        Json::Bool(b) => Value::Bool(*b),
        Json::Number(n) => n.as_i64().map(Value::Int).unwrap_or_else(|| Value::Float(n.as_f64().unwrap_or(0.0))),
        Json::String(s) => Value::Str(s.clone()),
        Json::Array(a) => Value::List(a.iter().map(to_value).collect()),
        Json::Object(o) => Value::Map(o.iter().map(|(k, v)| (k.clone(), to_value(v))).collect()),
    }
}

fn to_json(v: &Value) -> Json {
    match v {
        Value::Null => Json::Null,
        Value::Bool(b) => json!(b),
        Value::Int(i) => json!(i),
        Value::Float(f) => json!(f),
        Value::Str(s) => json!(s),
        Value::List(l) => Json::Array(l.iter().map(to_json).collect()),
        Value::Map(m) => Json::Object(m.iter().map(|(k, v)| (k.clone(), to_json(v))).collect()),
    }
}

fn get(p: &Payload, key: &str) -> Value {
    p.get(key).cloned().unwrap_or(Value::Null)
}

fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Int(i) => *i != 0,
        Value::Float(f) => *f != 0.0,
        Value::Str(s) => !s.is_empty(),
        Value::List(l) => !l.is_empty(),
        Value::Map(m) => !m.is_empty(),
    }
}

// One named type per operation: a step is identified by its type
// (conformance/API.md, "Step identity"); a single generic Op type would give
// every step the same identity (and dispatch on a string at every call).
fn key(spec: &Json, k: &str) -> String {
    spec[k].as_str().unwrap_or_default().to_string()
}

struct SetOp(String, Value);
impl Filter for SetOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        Ok(p.insert(&self.0, self.1.clone()))
    }
}
struct CopyOp(String, String);
impl Filter for CopyOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let v = get(&p, &self.0);
        Ok(p.insert(&self.1, v))
    }
}
struct AddOp(String, Value);
impl Filter for AddOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let next = match (p.get(&self.0).cloned().unwrap_or(Value::Int(0)), self.1.clone()) {
            (Value::Int(a), Value::Int(b)) => Value::Int(a + b),
            (a, b) => Value::Float(a.as_float().or(a.as_int().map(|x| x as f64)).unwrap_or(0.0)
                + b.as_float().or(b.as_int().map(|x| x as f64)).unwrap_or(0.0)),
        };
        Ok(p.insert(&self.0, next))
    }
}
struct AppendOp(String, Value);
impl Filter for AppendOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let mut list = match p.get(&self.0) {
            Some(Value::List(l)) => l.clone(),
            _ => Vec::new(),
        };
        list.push(self.1.clone());
        Ok(p.insert(&self.0, Value::List(list)))
    }
}
struct RemoveOp(String);
impl Filter for RemoveOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        Ok(p.remove(&self.0))
    }
}
struct MergeOp(Value);
impl Filter for MergeOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        match &self.0 {
            Value::Map(m) => Ok(p.merge(&Payload::from_data(m.clone()))),
            _ => Err("merge needs a map".into()),
        }
    }
}
struct HasOp(String, String);
impl Filter for HasOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let present = p.has(&self.0);
        Ok(p.insert(&self.1, Value::Bool(present)))
    }
}
struct MutateOp(String, Value);
impl Filter for MutateOp {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let mut m = p.with_mutation();
        m.set(&self.0, self.1.clone());
        Ok(m.to_immutable())
    }
}
struct FailOp(String);
impl Filter for FailOp {
    fn call(&self, _: Payload) -> Result<Payload, BoxError> {
        Err(self.0.clone().into())
    }
}
struct RecordTap(String);
impl Tap for RecordTap {
    fn observe(&self, p: &Payload) {
        TAPS.lock().unwrap().push(to_json(&get(p, &self.0)));
    }
}
struct FailTap(String);
impl Tap for FailTap {
    fn observe(&self, _: &Payload) {
        panic!("{}", self.0);
    }
}
struct NoopTap;
impl Tap for NoopTap {
    fn observe(&self, _: &Payload) {}
}
/// Configurable predicates: named types, the case's condition in their fields.
struct EqualsWhen(String, Json);
impl Predicate for EqualsWhen {
    fn test(&self, p: &Payload) -> bool {
        to_json(&get(p, &self.0)) == self.1
    }
}
struct TruthyWhen(String);
impl Predicate for TruthyWhen {
    fn test(&self, p: &Payload) -> bool {
        truthy(&get(p, &self.0))
    }
}
/// The runner's named pipeline type: only Nestable types can be nested.
struct Nested(Pipeline);
impl Nestable for Nested {
    fn into_pipeline(self) -> Pipeline {
        self.0
    }
}

/// Add a filter op (concrete type, so the step keeps its identity).
fn with_filter(p: Pipeline, spec: &Json) -> Result<Pipeline, String> {
    Ok(match spec["op"].as_str() {
        Some("set") => p.add_filter(SetOp(key(spec, "key"), to_value(&spec["value"]))),
        Some("copy") => p.add_filter(CopyOp(key(spec, "from"), key(spec, "to"))),
        Some("add") => p.add_filter(AddOp(key(spec, "key"), to_value(&spec["by"]))),
        Some("append") => p.add_filter(AppendOp(key(spec, "key"), to_value(&spec["value"]))),
        Some("remove") => p.add_filter(RemoveOp(key(spec, "key"))),
        Some("merge") => p.add_filter(MergeOp(to_value(&spec["value"]))),
        Some("has") => p.add_filter(HasOp(key(spec, "key"), key(spec, "to"))),
        Some("mutate") => p.add_filter(MutateOp(key(spec, "key"), to_value(&spec["value"]))),
        Some("fail") => p.add_filter(FailOp(key(spec, "message"))),
        other => return Err(format!("unknown filter op {other:?}")),
    })
}

/// Add a Valve: every (filter op, predicate) pair is a concrete type.
fn with_valve<P: Predicate + 'static>(p: Pipeline, spec: &Json, when: P) -> Result<Pipeline, String> {
    Ok(match spec["op"].as_str() {
        Some("set") => p.add_filter(Valve::new(SetOp(key(spec, "key"), to_value(&spec["value"])), when)),
        Some("copy") => p.add_filter(Valve::new(CopyOp(key(spec, "from"), key(spec, "to")), when)),
        Some("add") => p.add_filter(Valve::new(AddOp(key(spec, "key"), to_value(&spec["by"])), when)),
        Some("append") => p.add_filter(Valve::new(AppendOp(key(spec, "key"), to_value(&spec["value"])), when)),
        Some("remove") => p.add_filter(Valve::new(RemoveOp(key(spec, "key")), when)),
        Some("merge") => p.add_filter(Valve::new(MergeOp(to_value(&spec["value"])), when)),
        Some("has") => p.add_filter(Valve::new(HasOp(key(spec, "key"), key(spec, "to")), when)),
        Some("mutate") => p.add_filter(Valve::new(MutateOp(key(spec, "key"), to_value(&spec["value"])), when)),
        Some("fail") => p.add_filter(Valve::new(FailOp(key(spec, "message")), when)),
        other => return Err(format!("unknown filter op {other:?}")),
    })
}

struct RecordHook;

impl Hook for RecordHook {
    fn before(&self, name: Option<&str>, _: &Payload) {
        HOOKS.lock().unwrap().push(format!("before:{}", name.unwrap_or("")));
    }
    fn after(&self, name: Option<&str>, _: &Payload) {
        HOOKS.lock().unwrap().push(format!("after:{}", name.unwrap_or("")));
    }
    fn on_error(&self, name: Option<&str>, _: &(dyn std::error::Error + Send + Sync), _: &Payload) {
        HOOKS.lock().unwrap().push(format!("error:{}", name.unwrap_or("")));
    }
}

fn build(steps: &[Json]) -> Result<Pipeline, String> {
    let mut p = Pipeline::new();
    for s in steps {
        p = match s["kind"].as_str() {
            Some("filter") => with_filter(p, s)?,
            Some("tap") => match s["op"].as_str() {
                Some("record") => p.add_tap(RecordTap(key(s, "key"))),
                Some("fail") => p.add_tap(FailTap(key(s, "message"))),
                Some("noop") => p.add_tap(NoopTap),
                other => return Err(format!("unknown tap op {other:?}")),
            },
            Some("valve") => {
                let when = &s["when"];
                let k = key(when, "key");
                match when["op"].as_str() {
                    Some("equals") => with_valve(p, &s["filter"], EqualsWhen(k, to_json(&to_value(&when["value"]))))?,
                    Some("truthy") => with_valve(p, &s["filter"], TruthyWhen(k))?,
                    other => return Err(format!("unknown valve op {other:?}")),
                }
            }
            Some("pipeline") => {
                let child = build(s["steps"].as_array().map(Vec::as_slice).unwrap_or_default())?;
                p.add_pipeline(Nested(child))
            }
            other => return Err(format!("unknown step kind {other:?}")),
        };
    }
    Ok(p)
}

fn run_case(c: &Json) -> Json {
    TAPS.lock().unwrap().clear();
    HOOKS.lock().unwrap().clear();
    let id = c["id"].clone();
    let mut p = match build(c["steps"].as_array().map(Vec::as_slice).unwrap_or_default()) {
        Ok(p) => p,
        Err(reason) => return json!({"id": id, "unsupported": reason}),
    };
    let hooks = c["hooks"] == json!(true);
    if hooks {
        p = p.use_hook(Box::new(RecordHook));
    }
    let input = c.get("input").cloned().unwrap_or(json!({}));
    let data: HashMap<String, Value> = match to_value(&input) {
        Value::Map(m) => m,
        _ => HashMap::new(),
    };
    let mut result = Map::new();
    result.insert("id".into(), id);
    match catch_unwind(AssertUnwindSafe(|| p.run(Payload::from_data(data)))) {
        Ok(Ok(out)) => {
            result.insert("output".into(), to_json(&Value::Map(out.to_dict())));
        }
        Ok(Err(e)) => {
            result.insert("error".into(), json!(format!("Error: {e}")));
        }
        Err(panic) => {
            let message = panic
                .downcast_ref::<String>()
                .cloned()
                .or_else(|| panic.downcast_ref::<&str>().map(|s| s.to_string()))
                .unwrap_or_default();
            result.insert("error".into(), json!(format!("panic: {message}")));
        }
    }
    // Steps are identified by their type (conformance/API.md); the cases name
    // them. Each case step adds one pipeline step, in order: map identities
    // back. An identity this map does not know stays as is and fails.
    let names: Vec<String> = c["steps"].as_array().map(|a| {
        a.iter().map(|s| s["name"].as_str().unwrap_or_default().to_string()).collect()
    }).unwrap_or_default();
    let label: HashMap<String, String> = p.identities().into_iter().zip(names).collect();
    let named = |ids: &[String]| -> Vec<String> {
        ids.iter().map(|i| label.get(i).cloned().unwrap_or_else(|| i.clone())).collect()
    };
    let state = p.state();
    let errors: Vec<String> = state.errors.iter().map(|(n, _)| n.clone()).collect();
    result.insert("state".into(), json!({
        "executed": named(&state.executed),
        "skipped": named(&state.skipped),
        "errors": named(&errors),
    }));
    if hooks {
        let mapped: Vec<String> = HOOKS.lock().unwrap().iter().map(|h| {
            let (phase, id) = h.split_once(':').unwrap_or((h.as_str(), ""));
            format!("{phase}:{}", label.get(id).map(String::as_str).unwrap_or(id))
        }).collect();
        result.insert("hooks".into(), json!(mapped));
    }
    result.insert("taps".into(), Json::Array(TAPS.lock().unwrap().clone()));
    result.insert("input_after".into(), input);
    Json::Object(result)
}

struct NoopHook;
impl Hook for NoopHook {}

const BENCH_WARMUP: usize = 20000;
const BENCH_RUNS: usize = 20000;
const BENCH_REPEATS: usize = 5;

/// Best of BENCH_REPEATS x BENCH_RUNS, in µs per run.
fn bench(cases: &[Json]) -> Vec<Json> {
    cases
        .iter()
        .map(|c| {
            let mut p = match build(c["steps"].as_array().map(Vec::as_slice).unwrap_or_default()) {
                Ok(p) => p,
                Err(reason) => return json!({"id": c["id"], "unsupported": reason}),
            };
            if c["hooks"] == json!("noop") {
                p = p.use_hook(Box::new(NoopHook));
            }
            let data: HashMap<String, Value> = match to_value(&c["input"]) {
                Value::Map(m) => m,
                _ => HashMap::new(),
            };
            let output = to_json(&Value::Map(p.run(Payload::from_data(data.clone())).unwrap().to_dict()));
            for _ in 0..BENCH_WARMUP {
                let _ = p.run(Payload::from_data(data.clone()));
            }
            let mut best = std::time::Duration::MAX;
            for _ in 0..BENCH_REPEATS {
                let t0 = std::time::Instant::now();
                for _ in 0..BENCH_RUNS {
                    let _ = std::hint::black_box(p.run(Payload::from_data(data.clone())));
                }
                best = best.min(t0.elapsed());
            }
            let us = best.as_nanos() as f64 / BENCH_RUNS as f64 / 1000.0;
            json!({"id": c["id"], "us_per_run": us, "output": output})
        })
        .collect()
}

fn main() {
    // Tap panics are expected cases; keep their default report off stderr noise.
    std::panic::set_hook(Box::new(|_| {}));
    let mut text = String::new();
    std::io::stdin().read_to_string(&mut text).expect("read stdin");
    let cases: Vec<Json> = serde_json::from_str(&text).expect("cases json");
    let results: Vec<Json> = if std::env::args().nth(1).as_deref() == Some("bench") {
        bench(&cases)
    } else {
        cases.iter().map(run_case).collect()
    };
    println!("{}", Json::Array(results));
}

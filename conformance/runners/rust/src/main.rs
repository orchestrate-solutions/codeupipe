//! Rust conformance runner: runs the cases and reports what happened.
//!
//!     runner <target> < cases.json > results.json
//!
//! Targets
//!     run         the Pipeline of packages/codeupipe-rs
//!     bench:run   the same, timed on the scenarios of conformance/bench
//!
//! The runner never judges; conformance/run.py compares the results of every
//! target with the same expectations.
mod bench;
mod cup_ops;
mod json;

use std::cell::RefCell;
use std::collections::HashMap;
use std::io::{self, Read, Write};
use std::process::ExitCode;
use std::rc::Rc;

use codeupipe::{Filter, Map, Payload, Pipeline, Predicate, Value};
use cup_ops::{
    sink, AddFilter, AppendFilter, CopyFilter, EqualsPredicate, FailFilter, FailTap, HasFilter,
    MergeFilter, MutateFilter, NestedPipeline, NoopHook, NoopTap, RecordHook, RecordTap,
    RemoveFilter, SetFilter, TruthyPredicate,
};

/// A case that this runner cannot express. It is reported, never judged.
struct Unsupported(String);

fn field<'a>(spec: &'a Map, name: &str) -> Result<&'a Value, Unsupported> {
    spec.get(name)
        .ok_or_else(|| Unsupported(format!("the step has no '{name}'")))
}

fn text(spec: &Map, name: &str) -> Result<String, Unsupported> {
    field(spec, name)?
        .as_str()
        .map(str::to_string)
        .ok_or_else(|| Unsupported(format!("'{name}' is not a string")))
}

fn number(spec: &Map, name: &str) -> Result<f64, Unsupported> {
    field(spec, name)?
        .as_f64()
        .ok_or_else(|| Unsupported(format!("'{name}' is not a number")))
}

fn map<'a>(spec: &'a Map, name: &str) -> Result<&'a Map, Unsupported> {
    field(spec, name)?
        .as_map()
        .ok_or_else(|| Unsupported(format!("'{name}' is not an object")))
}

fn value(spec: &Map, name: &str) -> Result<Value, Unsupported> {
    field(spec, name).cloned()
}

/// Where a Filter goes: alone, or behind a Predicate. `add_filter` and
/// `add_valve` take the type of the step, which gives its label, so the
/// Filter is handed over by its own type and not as a `Box<dyn Filter>`.
trait UseFilter {
    fn add<F: Filter + 'static>(self, filter: F);
}

struct AsFilter<'a>(&'a mut Pipeline);

impl UseFilter for AsFilter<'_> {
    fn add<F: Filter + 'static>(self, filter: F) {
        self.0.add_filter(filter);
    }
}

struct AsValve<'a, P>(&'a mut Pipeline, P);

impl<P: Predicate + 'static> UseFilter for AsValve<'_, P> {
    fn add<F: Filter + 'static>(self, filter: F) {
        self.0.add_valve(self.1, filter);
    }
}

fn add_filter(spec: &Map, to: impl UseFilter) -> Result<(), Unsupported> {
    match text(spec, "op")?.as_str() {
        "set" => to.add(SetFilter {
            key: text(spec, "key")?,
            value: value(spec, "value")?,
        }),
        "copy" => to.add(CopyFilter {
            from: text(spec, "from")?,
            to: text(spec, "to")?,
        }),
        "add" => to.add(AddFilter {
            key: text(spec, "key")?,
            by: number(spec, "by")?,
        }),
        "append" => to.add(AppendFilter {
            key: text(spec, "key")?,
            value: value(spec, "value")?,
        }),
        "remove" => to.add(RemoveFilter {
            key: text(spec, "key")?,
        }),
        "merge" => to.add(MergeFilter {
            value: map(spec, "value")?.clone(),
        }),
        "has" => to.add(HasFilter {
            key: text(spec, "key")?,
            to: text(spec, "to")?,
        }),
        "mutate" => to.add(MutateFilter {
            key: text(spec, "key")?,
            value: value(spec, "value")?,
        }),
        "fail" => to.add(FailFilter {
            message: text(spec, "message")?,
        }),
        "run_again" => {
            return Err(Unsupported(
                "a run inside a run of the same pipeline is not in the Rust runtime yet"
                    .to_string(),
            ))
        }
        op => return Err(Unsupported(format!("unknown filter op '{op}'"))),
    }
    Ok(())
}

fn add_tap(spec: &Map, pipeline: &mut Pipeline) -> Result<(), Unsupported> {
    match text(spec, "op")?.as_str() {
        "record" => pipeline.add_tap(RecordTap {
            key: text(spec, "key")?,
        }),
        "fail" => pipeline.add_tap(FailTap {
            message: text(spec, "message")?,
        }),
        "noop" => pipeline.add_tap(NoopTap),
        op => return Err(Unsupported(format!("unknown tap op '{op}'"))),
    }
    Ok(())
}

fn add_valve(when: &Map, filter: &Map, pipeline: &mut Pipeline) -> Result<(), Unsupported> {
    match text(when, "op")?.as_str() {
        "equals" => {
            let predicate = EqualsPredicate {
                key: text(when, "key")?,
                value: value(when, "value")?,
            };
            add_filter(filter, AsValve(pipeline, predicate))
        }
        "truthy" => {
            let predicate = TruthyPredicate {
                key: text(when, "key")?,
            };
            add_filter(filter, AsValve(pipeline, predicate))
        }
        op => Err(Unsupported(format!("unknown valve op '{op}'"))),
    }
}

fn steps_of(spec: &Map) -> Result<&[Value], Unsupported> {
    field(spec, "steps")?
        .as_list()
        .ok_or_else(|| Unsupported("'steps' is not a list".to_string()))
}

fn build(steps: &[Value], pipeline: &mut Pipeline) -> Result<(), Unsupported> {
    for step in steps {
        let step = step
            .as_map()
            .ok_or_else(|| Unsupported("a step is not an object".to_string()))?;
        match text(step, "kind")?.as_str() {
            "filter" => add_filter(step, AsFilter(pipeline))?,
            "tap" => add_tap(step, pipeline)?,
            "valve" => add_valve(map(step, "when")?, map(step, "filter")?, pipeline)?,
            "pipeline" => {
                let mut inner = Pipeline::named(NestedPipeline);
                build(steps_of(step)?, &mut inner)?;
                pipeline.add_pipeline(inner);
            }
            kind => return Err(Unsupported(format!("unknown step kind '{kind}'"))),
        }
    }
    Ok(())
}

/// Label to the step name of the case. The cases name their steps, and the
/// runtime reports labels (conformance/API.md). The steps are added in the
/// order of the case, so the two lists are side by side. A label that the
/// runtime reports and that is not in this map stays as it is, and fails the
/// comparison.
fn names_by_label(pipeline: &Pipeline, steps: &[Value]) -> HashMap<String, String> {
    pipeline
        .labels()
        .into_iter()
        .zip(steps)
        .map(|(label, step)| {
            let name = step.as_map().and_then(|step| step.get("name"));
            (
                label,
                name.and_then(Value::as_str).unwrap_or("").to_string(),
            )
        })
        .collect()
}

fn names(labels: &[String], named: &impl Fn(&str) -> String) -> Value {
    Value::List(
        labels
            .iter()
            .map(|label| Value::from(named(label)))
            .collect(),
    )
}

fn run_case(spec: &Map) -> Result<Value, Unsupported> {
    if spec.get("given_state") == Some(&Value::Bool(true)) {
        return Err(Unsupported(
            "a run with a State from the caller, run(p, state), is not in the Rust runtime yet"
                .to_string(),
        ));
    }
    let steps = steps_of(spec)?;
    let mut pipeline = Pipeline::new();
    build(steps, &mut pipeline)?;
    let by_label = names_by_label(&pipeline, steps);
    let named = |label: &str| {
        by_label
            .get(label)
            .cloned()
            .unwrap_or_else(|| label.to_string())
    };
    let hooks = spec.get("hooks") == Some(&Value::Bool(true));
    let events = Rc::new(RefCell::new(Vec::new()));
    if hooks {
        pipeline.use_hook(RecordHook {
            events: Rc::clone(&events),
        });
    }

    let input = Payload::from_map(map(spec, "input")?.clone());
    let mut result = Map::new();
    result.insert("id", value(spec, "id")?);
    match pipeline.run(&input) {
        Ok(output) => result.insert("output", output.to_dict()),
        Err(error) => result.insert("error", error.to_string()),
    };
    let state = pipeline.state();
    let errors: Vec<String> = state
        .errors()
        .iter()
        .map(|(label, _)| label.clone())
        .collect();
    result.insert(
        "state",
        Map::from([
            ("executed", names(state.executed(), &named)),
            ("skipped", names(state.skipped(), &named)),
            ("errors", names(&errors, &named)),
        ]),
    );
    result.insert("taps", sink::take());
    if hooks {
        let events: Vec<Value> = events
            .borrow()
            .iter()
            .map(|event| {
                let (kind, label) = event.split_once(':').unwrap_or((event, ""));
                let step = if label.is_empty() {
                    String::new()
                } else {
                    named(label)
                };
                Value::from(format!("{kind}:{step}"))
            })
            .collect();
        result.insert("hooks", Value::List(events));
    }
    result.insert("input_after", input.to_dict());
    Ok(Value::Map(result))
}

fn bench_case(spec: &Map) -> Result<Value, Unsupported> {
    let mut pipeline = Pipeline::new();
    build(steps_of(spec)?, &mut pipeline)?;
    if spec.get("hooks") == Some(&Value::from("noop")) {
        pipeline.use_hook(NoopHook);
    }
    let input = Payload::from_map(map(spec, "input")?.clone());
    Ok(bench::bench(value(spec, "id")?, pipeline, input))
}

fn main() -> ExitCode {
    let target = std::env::args().nth(1).unwrap_or_default();
    let run: fn(&Map) -> Result<Value, Unsupported> = match target.as_str() {
        "run" => run_case,
        "bench:run" => bench_case,
        _ => {
            eprintln!("unknown target '{target}'. The targets are: run, bench:run");
            return ExitCode::from(2);
        }
    };
    let mut text = String::new();
    if let Err(error) = io::stdin().read_to_string(&mut text) {
        eprintln!("cannot read the cases: {error}");
        return ExitCode::from(2);
    }
    let cases = match json::read(&text) {
        Ok(Value::List(cases)) => cases,
        Ok(_) => {
            eprintln!("the cases are not a list");
            return ExitCode::from(2);
        }
        Err(error) => {
            eprintln!("cannot read the cases: {error}");
            return ExitCode::from(2);
        }
    };

    let mut results = Vec::new();
    for case in &cases {
        sink::take();
        let Some(spec) = case.as_map() else {
            eprintln!("a case is not an object");
            return ExitCode::from(2);
        };
        results.push(match run(spec) {
            Ok(result) => result,
            Err(Unsupported(reason)) => Value::Map(Map::from([
                ("id", spec.get("id").cloned().unwrap_or(Value::Null)),
                ("unsupported", Value::from(reason)),
            ])),
        });
    }
    let mut out = io::stdout().lock();
    if writeln!(out, "{}", json::write(&Value::List(results))).is_err() {
        return ExitCode::from(2);
    }
    ExitCode::SUCCESS
}

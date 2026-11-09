use codeupipe::{Filter, StepError};

use crate::laid_out::LaidOut;
use crate::layout_run::LayoutRun;
use crate::layout_step::LayoutStep;
use crate::refusal::Refusal;

/// The calls and the `use` lines of each pipeline of the layout
/// (conformance/ADD.md, "The steps").
///
/// Reads `components`. Writes, for each component, `calls` (the method and
/// the type names of each call, steps first, then hooks) and `uses` (the
/// module and the type of each step, sorted). A name that is not a component,
/// a step of the wrong kind, or a pipeline that has itself as a step is
/// refused with exit code 2.
pub struct ResolveStepsFilter;

impl Filter<LayoutRun> for ResolveStepsFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        let found = run.components.clone();
        for component in &mut run.components {
            resolve(component, &found)?;
        }
        for component in &run.components {
            refuse_a_loop(component, &run.components, &mut Vec::new())?;
        }
        Ok(())
    }
}

/// The call that a step of `kind` gives: a predicate and a hook are not steps.
// cup: allow-plain a lookup of the call for a kind: it chooses a method name, and is not a step
fn call_of(kind: &str) -> &'static str {
    match kind {
        "tap" => "add_tap",
        "pipeline" => "add_pipeline",
        _ => "add_filter",
    }
}

/// The component that `name` (its name or its type name) is.
fn find<'a>(name: &str, found: &'a [LaidOut], component: &LaidOut) -> Result<&'a LaidOut, Refusal> {
    found
        .iter()
        .find(|used| used.name == name || used.type_name == name)
        .ok_or_else(|| {
            Refusal::usage(format!(
                "{name}, a step of {}, is not a component of the layout.",
                component.name
            ))
        })
}

// cup: allow-plain the steps of one pipeline: a rule of ResolveStepsFilter, not a step
fn resolve(component: &mut LaidOut, found: &[LaidOut]) -> Result<(), Refusal> {
    let mut calls: Vec<(String, Vec<&LaidOut>)> = Vec::new();
    for step in &component.steps {
        match step {
            LayoutStep::Valve(predicate, filter) => {
                let pair = [
                    find(predicate, found, component)?,
                    find(filter, found, component)?,
                ];
                for (used, wanted) in pair.iter().zip(["predicate", "filter"]) {
                    if used.kind != wanted {
                        return Err(Refusal::usage(format!(
                            "valve: [{predicate}, {filter}] in {}: a valve is [Predicate, Filter], and {} is a {}, not a {wanted}.",
                            component.name, used.name, used.kind
                        )));
                    }
                }
                calls.push(("add_valve".to_string(), pair.to_vec()));
            }
            LayoutStep::Name(name) => {
                let used = find(name, found, component)?;
                if used.kind == "predicate" {
                    return Err(Refusal::usage(format!(
                        "{0} is a predicate. A predicate is not a step: put it in a valve: [{0}, Filter].",
                        used.name
                    )));
                }
                if used.kind == "hook" {
                    return Err(Refusal::usage(format!(
                        "{} is a hook. A hook is not a step: put it in hooks: of {}.",
                        used.name, component.name
                    )));
                }
                calls.push((call_of(&used.kind).to_string(), vec![used]));
            }
        }
    }
    for name in &component.hooks {
        let hook = find(name, found, component)?;
        if hook.kind != "hook" {
            return Err(Refusal::usage(format!(
                "{name} in the hooks of {} is a {}, not a hook.",
                component.name, hook.kind
            )));
        }
        calls.push(("use_hook".to_string(), vec![hook]));
    }
    let mut uses: Vec<(String, String)> = calls
        .iter()
        .flat_map(|(_, used)| {
            used.iter()
                .map(|used| (used.module.clone(), used.type_name.clone()))
        })
        .collect();
    uses.sort();
    uses.dedup();
    component.calls = calls
        .into_iter()
        .map(|(method, used)| {
            (
                method,
                used.iter().map(|used| used.type_name.clone()).collect(),
            )
        })
        .collect();
    component.uses = uses;
    Ok(())
}

// cup: allow-plain a walk of the nested pipelines: a rule of ResolveStepsFilter, not a step
fn refuse_a_loop(
    component: &LaidOut,
    all: &[LaidOut],
    path: &mut Vec<String>,
) -> Result<(), Refusal> {
    if let Some(at) = path
        .iter()
        .position(|type_name| *type_name == component.type_name)
    {
        let mut cycle = path[at..].to_vec();
        cycle.push(component.type_name.clone());
        return Err(Refusal::usage(format!(
            "A pipeline has itself as a step: {}.",
            cycle.join(" -> ")
        )));
    }
    path.push(component.type_name.clone());
    for (method, names) in &component.calls {
        if method != "add_pipeline" {
            continue;
        }
        if let Some(nested) = all
            .iter()
            .find(|used| Some(&used.type_name) == names.first())
        {
            refuse_a_loop(nested, all, path)?;
        }
    }
    path.pop();
    Ok(())
}

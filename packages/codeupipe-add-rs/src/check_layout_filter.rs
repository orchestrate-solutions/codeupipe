use codeupipe::{Filter, StepError};

use crate::laid_out::LaidOut;
use crate::layout_run::LayoutRun;
use crate::layout_step::LayoutStep;
use crate::layout_value::LayoutValue;
use crate::refusal::Refusal;

/// The language of this command: a layout for another one is refused.
pub const LANG: &str = "rust";
/// The keys of a layout (conformance/ADD.md, "The keys").
pub const LAYOUT_KEYS: [&str; 3] = ["lang", "root", "components"];
/// The keys of a component.
pub const COMPONENT_KEYS: [&str; 5] = ["kind", "name", "description", "steps", "hooks"];

/// The keys of the layout, and the shape of each.
///
/// Reads `layout`. Writes `directory` (`root:`, or `src`, the Rust default of
/// phase 1) and `components`, in the order of the file. A key that is not
/// known, a key that is missing, or a value of the wrong shape is refused
/// with exit code 2. The names are checked by the next steps.
pub struct CheckLayoutFilter;

impl Filter<LayoutRun> for CheckLayoutFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        let layout = run.layout.clone().unwrap_or(LayoutValue::Map(Vec::new()));
        known(&layout, &LAYOUT_KEYS, "the layout")?;
        let lang = layout.get("lang").ok_or_else(|| {
            Refusal::usage(format!(
                "The layout has no lang:. For this command it is lang: {LANG}."
            ))
        })?;
        if lang.as_text() != Some(LANG) {
            let shown = lang.as_text().map_or_else(|| lang.shown(), str::to_string);
            return Err(Refusal::usage(format!(
                "The layout is for {shown}, and this is codeupipe add for {LANG}."
            ))
            .into());
        }
        run.directory = match layout.get("root") {
            None => "src".to_string(),
            Some(LayoutValue::Text(root)) if !root.is_empty() => root.clone(),
            Some(_) => {
                return Err(Refusal::usage("root: is a directory, such as src/pricing.").into())
            }
        };
        let listed =
            match layout.get("components") {
                Some(LayoutValue::List(items)) if !items.is_empty() => items.clone(),
                _ => return Err(Refusal::usage(
                    "components: is a list with one component or more, each with kind: and name:.",
                )
                .into()),
            };
        run.components = listed.iter().map(component).collect::<Result<_, _>>()?;
        Ok(())
    }
}

/// A key of `mapping` that is not one of `keys` is refused, with the keys.
// cup: allow-plain a rule of the step on one mapping: it names the keys that the contract does not know
fn known(mapping: &LayoutValue, keys: &[&str], label: &str) -> Result<(), Refusal> {
    let LayoutValue::Map(pairs) = mapping else {
        return Ok(());
    };
    let unknown: Vec<&str> = pairs
        .iter()
        .map(|(key, _)| key.as_str())
        .filter(|key| !keys.contains(key))
        .collect();
    if unknown.is_empty() {
        return Ok(());
    }
    Err(Refusal::usage(format!(
        "Unknown key {} in {label}. The keys are: {}.",
        unknown.join(", "),
        keys.join(", ")
    )))
}

/// One component of the list, with each key of COMPONENT_KEYS.
// cup: allow-plain the shape of one component: a rule of CheckLayoutFilter, not a step
fn component(item: &LayoutValue) -> Result<LaidOut, Refusal> {
    if !matches!(item, LayoutValue::Map(_)) {
        return Err(Refusal::usage(format!(
            "A component is a mapping with kind: and name:, not {}.",
            item.shown()
        )));
    }
    let label = match item.get("name").and_then(LayoutValue::as_text) {
        Some(name) => format!("the component {name}"),
        None => "the component with no name".to_string(),
    };
    known(item, &COMPONENT_KEYS, &label)?;
    let text = |key: &str| {
        item.get(key)
            .and_then(LayoutValue::as_text)
            .map(str::to_string)
            .ok_or_else(|| Refusal::usage(format!("The{} has no {key}:.", &label["the".len()..])))
    };
    let kind = text("kind")?;
    let name = text("name")?;
    let description = match item.get("description") {
        None => String::new(),
        Some(LayoutValue::Text(description)) => description.clone(),
        Some(_) => {
            return Err(Refusal::usage(format!(
                "The description of {label} is not a text."
            )))
        }
    };
    for key in ["steps", "hooks"] {
        if item.get(key).is_some() && kind != "pipeline" {
            return Err(Refusal::usage(format!(
                "{key}: is only for a pipeline, and {name} is a {kind}."
            )));
        }
    }
    let steps = match item.get("steps") {
        None => Vec::new(),
        Some(LayoutValue::List(steps)) => steps
            .iter()
            .map(|step| {
                step_of(step).ok_or_else(|| {
                    Refusal::usage(format!(
                        "The step {} of {name} cannot be read. A step is a name, or valve: [Predicate, Filter].",
                        step.shown()
                    ))
                })
            })
            .collect::<Result<_, _>>()?,
        Some(_) => {
            return Err(Refusal::usage(format!(
                "The steps of {name} are a list. A step is a name, or valve: [Predicate, Filter]."
            )))
        }
    };
    let hooks = match item.get("hooks") {
        None => Vec::new(),
        Some(LayoutValue::List(hooks)) if hooks.iter().all(|hook| hook.as_text().is_some()) => {
            hooks
                .iter()
                .filter_map(LayoutValue::as_text)
                .map(str::to_string)
                .collect()
        }
        Some(_) => {
            return Err(Refusal::usage(format!(
                "The hooks of {name} are a list of names."
            )))
        }
    };
    Ok(LaidOut {
        kind,
        name,
        description,
        steps,
        hooks,
        ..LaidOut::default()
    })
}

/// A name, or a mapping with only `valve`, whose value is two names.
// cup: allow-plain the shape of one step: a rule of CheckLayoutFilter, not a step
fn step_of(step: &LayoutValue) -> Option<LayoutStep> {
    match step {
        LayoutValue::Text(name) => Some(LayoutStep::Name(name.clone())),
        LayoutValue::Map(pairs) if pairs.len() == 1 && pairs[0].0 == "valve" => match &pairs[0].1 {
            LayoutValue::List(pair) => match pair.as_slice() {
                [LayoutValue::Text(predicate), LayoutValue::Text(filter)] => {
                    Some(LayoutStep::Valve(predicate.clone(), filter.clone()))
                }
                _ => None,
            },
            _ => None,
        },
        _ => None,
    }
}

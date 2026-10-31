use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::templates;

/// The text of the component file and of the test file.
///
/// Reads `kind`, `type_name`, `snake`, `component_path`, `crate_name` and
/// `description`, and, for a pipeline of a layout, `calls` and `uses`. Writes
/// `component_text` and `test_text`. With no description, the header says
/// `TODO: say what <TypeName> does.` A pipeline with calls gets its steps.
pub struct RenderFilesFilter;

impl Filter<AddRun> for RenderFilesFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let description = if run.description.is_empty() {
            format!("TODO: say what {} does.", run.type_name)
        } else {
            run.description.replace('\n', " ")
        };
        let module = module_of(&run.component_path);
        let template = if run.calls.is_empty() {
            template_of(&run.kind)
        } else {
            templates::PIPELINE_STEPS
        };
        run.component_text = fill(template, run, &description, &module);
        run.test_text = fill(templates::TEST, run, &description, &module);
        Ok(())
    }
}

/// The template of `kind`. The five kinds are the ones of the contract, and
/// TypeNameFilter refused any other before this step.
// cup: allow-plain a lookup of the text for a kind: it chooses a template, and is not a step
fn template_of(kind: &str) -> &'static str {
    match kind {
        "predicate" => templates::PREDICATE,
        "tap" => templates::TAP,
        "hook" => templates::HOOK,
        "pipeline" => templates::PIPELINE,
        _ => templates::FILTER,
    }
}

/// The module path of the component in the crate: `src/pricing/discount_filter.rs`
/// gives `pricing.discount_filter`, and `src/discount_filter.rs` gives
/// `discount_filter`, because `src` is the crate itself.
// cup: allow-plain a path rule of the contract: it turns a file path into a module path
pub(crate) fn module_of(component_path: &str) -> String {
    let path = component_path
        .trim_matches('/')
        .trim_end_matches(".rs")
        .replace('/', "::");
    match path.strip_prefix("src::") {
        Some(rest) => rest.to_string(),
        None => path,
    }
}

/// The text of `template` with the values of the run in place of each
/// placeholder. A placeholder is `{` NAME `}`, and NAME has letters, digits
/// and `_` only; any other brace is a brace of Rust
/// (`use codeupipe::{Filter, Payload};`) and stays as it is.
// cup: allow-plain the filling of a template: it joins text, and is not a step
fn fill(template: &str, run: &AddRun, description: &str, module: &str) -> String {
    let mut text = String::with_capacity(template.len());
    let mut rest = template;
    while let Some(at) = rest.find('{') {
        text.push_str(&rest[..at]);
        rest = &rest[at + 1..];
        let Some(end) = rest.find('}') else {
            text.push('{');
            continue;
        };
        let name = &rest[..end];
        if !is_placeholder(name) {
            text.push('{');
            continue;
        }
        let lines;
        text.push_str(match name {
            "uses" => {
                lines = uses_of(run);
                &lines
            }
            "calls" => {
                lines = calls_of(run);
                &lines
            }
            "type_name" => &run.type_name,
            "snake" => &run.snake,
            "description" => description,
            "module" => module,
            "crate_name" => &run.crate_name,
            _ => &rest[..=end],
        });
        rest = &rest[end + 1..];
    }
    text.push_str(rest);
    text
}

/// The `use` line of each step of a pipeline of a layout.
fn uses_of(run: &AddRun) -> String {
    run.uses
        .iter()
        .map(|(module, type_name)| format!("use crate::{module}::{type_name};"))
        .collect::<Vec<_>>()
        .join("\n")
}

/// The line of each call of a pipeline of a layout. Each step is made with no
/// arguments, as each component of phase 1 is: a unit struct. A nested
/// pipeline is `Pipeline::named(...)`.
// cup: allow-plain the filling of a template: it joins text, and is not a step
fn calls_of(run: &AddRun) -> String {
    run.calls
        .iter()
        .map(|(method, types)| {
            let arguments: Vec<String> = types
                .iter()
                .map(|type_name| match method.as_str() {
                    "add_pipeline" => format!("Pipeline::named({type_name})"),
                    _ => type_name.clone(),
                })
                .collect();
            format!("        pipeline.{method}({});", arguments.join(", "))
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// A placeholder name: not empty, and nothing but letters, digits and `_`.
/// So `{Filter, Payload}` and `{{` are not placeholders.
fn is_placeholder(name: &str) -> bool {
    !name.is_empty() && name.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
}

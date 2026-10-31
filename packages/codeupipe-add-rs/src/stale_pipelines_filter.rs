use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::layout_run::LayoutRun;

/// The calls that a step of a pipeline makes.
const CALLS: [&str; 5] = [
    "add_filter",
    "add_valve",
    "add_tap",
    "add_pipeline",
    "use_hook",
];

/// A kept pipeline file whose steps are not those of the layout.
///
/// Reads `root`, `components` and `kept`. Writes `stale`: the path of each
/// kept pipeline file whose steps (the method and the types of each call, in
/// order) are not those that the layout gives. The arguments and the
/// comments do not count, so a file that a user filled in is not stale while
/// its steps are the same.
pub struct StalePipelinesFilter;

impl Filter<LayoutRun> for StalePipelinesFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        let root = Path::new(&run.root);
        run.stale = run
            .components
            .iter()
            .filter(|component| {
                component.kind == "pipeline" && run.kept.contains(&component.component_path)
            })
            .filter(|component| {
                let on_disk =
                    fs::read_to_string(root.join(&component.component_path)).unwrap_or_default();
                steps(&on_disk) != steps(&component.component_text)
            })
            .map(|component| component.component_path.clone())
            .collect();
        Ok(())
    }
}

/// The method and the types of each call of a step, in order.
// cup: allow-plain a reading of the calls in a text: it compares text, and is not a step
fn steps(text: &str) -> Vec<(String, Vec<String>)> {
    let code = without_comments(text);
    let mut found = Vec::new();
    let mut at = 0;
    while let Some((start, method)) = next_call(&code, at) {
        let open = start + method.len() + 2;
        let mut depth = 1;
        let mut end = open;
        for (offset, character) in code[open..].char_indices() {
            depth += match character {
                '(' => 1,
                ')' => -1,
                _ => 0,
            };
            if depth == 0 {
                end = open + offset;
                break;
            }
            end = open + offset + character.len_utf8();
        }
        found.push((method.to_string(), types(&code[open..end])));
        at = end;
    }
    found
}

/// The first `.add_filter(` (or another call of CALLS) at or after `at`.
fn next_call(code: &str, at: usize) -> Option<(usize, &'static str)> {
    CALLS
        .iter()
        .filter_map(|method| {
            code[at..]
                .find(&format!(".{method}("))
                .map(|found| (at + found, *method))
        })
        .min_by_key(|(found, _)| *found)
}

/// The type names in the arguments of a call: a word that starts with a
/// capital and has a small letter (so `RATE`, a constant, is not one).
fn types(arguments: &str) -> Vec<String> {
    arguments
        .split(|c: char| !(c.is_alphanumeric() || c == '_'))
        .filter(|word| {
            word.starts_with(|c: char| c.is_ascii_uppercase())
                && word.chars().any(|c| c.is_ascii_lowercase())
        })
        .map(str::to_string)
        .collect()
}

/// The code with each `//` comment and `/* */` comment taken out.
// cup: allow-plain the text of a file with no comments: it is text, not a step
fn without_comments(text: &str) -> String {
    let mut code = String::with_capacity(text.len());
    let mut rest = text;
    while !rest.is_empty() {
        if let Some(after) = rest.strip_prefix("//") {
            rest = after.find('\n').map_or("", |end| &after[end..]);
        } else if let Some(after) = rest.strip_prefix("/*") {
            rest = after.find("*/").map_or("", |end| &after[end + 2..]);
        } else {
            let character = rest.chars().next().unwrap_or_default();
            code.push(character);
            rest = &rest[character.len_utf8()..];
        }
    }
    code
}

use std::fs;

use codeupipe::{Filter, StepError};

use crate::finding::Finding;
use crate::lint_run::LintRun;
use crate::markers::markers_of;
use crate::rules::{rule, PARSE_ERROR};
use crate::source::{position, Source};

/// Reads and parses each file.
///
/// Reads `files`. Writes `sources` (the files that parse, with their
/// `cup: allow-...` comments), a CUP-I000 finding for a file with a syntax
/// error, and `errors` for a file that cannot be read.
pub struct ParseFilesFilter;

impl Filter<LintRun> for ParseFilesFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        for path in run.files.clone() {
            let text = match fs::read_to_string(&path) {
                Ok(text) => text,
                Err(error) => {
                    run.errors.push(format!("{path}: {error}"));
                    continue;
                }
            };
            match syn::parse_file(&text) {
                Ok(tree) => run.sources.push(Source {
                    markers: markers_of(&text),
                    path,
                    text,
                    tree,
                }),
                Err(error) => {
                    let (line, col) = position(error.span());
                    let parse_error = rule(PARSE_ERROR).expect("a rule");
                    run.findings.push(Finding {
                        path,
                        line,
                        col,
                        rule: PARSE_ERROR.to_string(),
                        slug: parse_error.slug.to_string(),
                        message: format!("{error}. {}", parse_error.fix),
                        call_line: None,
                        warning: false,
                    });
                }
            }
        }
        Ok(())
    }
}

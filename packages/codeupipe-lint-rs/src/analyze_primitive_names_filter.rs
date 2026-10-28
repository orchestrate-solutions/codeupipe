use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::lint_run::LintRun;
use crate::primitive_kind::{is_test_file, primitives_in};
use crate::rules::{make_finding, PRIMITIVE_FILE_NAME, PRIMITIVE_ROLE_SUFFIX};

/// CUP-I007: the type name of a primitive ends with its role
/// (`DiscountFilter`, `AuditTap`, `PrintStepsHook`, `AtLeastPredicate`,
/// `PricingPipeline`).
///
/// CUP-I006: the file name is the type name in snake_case
/// (`discount_filter.rs`).
///
/// Checked: the primitives at the top level of a file. Not checked: plain
/// types, and the files of `tests/`.
///
/// Reads `sources`. Writes `findings`.
pub struct AnalyzePrimitiveNamesFilter;

impl Filter<LintRun> for AnalyzePrimitiveNamesFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        for source in run
            .sources
            .iter()
            .filter(|source| !is_test_file(&source.path))
        {
            let file = Path::new(&source.path)
                .file_name()
                .unwrap_or_default()
                .to_string_lossy();
            let (stem, extension) = file.split_at(file.find('.').unwrap_or(file.len()));
            for primitive in primitives_in(&source.tree.items) {
                let role = primitive.kind.name();
                let mut wanted = primitive.name.clone();
                if !wanted.ends_with(role) {
                    wanted.push_str(role);
                    let what = format!(
                        "{role} `{}` does not say what it is. Name it `{wanted}`",
                        primitive.name
                    );
                    let finding =
                        make_finding(source, primitive.at, PRIMITIVE_ROLE_SUFFIX, &what, None);
                    run.findings.push(finding);
                }
                let snake = Self::snake_case(&wanted);
                if stem != snake {
                    let what = format!("`{wanted}` is in `{file}`. Put it in `{snake}{extension}`");
                    let finding =
                        make_finding(source, primitive.at, PRIMITIVE_FILE_NAME, &what, None);
                    run.findings.push(finding);
                }
            }
        }
        Ok(())
    }
}

impl AnalyzePrimitiveNamesFilter {
    /// `ParseHTMLFilter` gives `parse_html_filter`.
    pub fn snake_case(name: &str) -> String {
        let chars: Vec<char> = name.chars().collect();
        let mut out = String::new();
        for (index, c) in chars.iter().enumerate() {
            let before = index.checked_sub(1).map(|i| chars[i]);
            let after = chars.get(index + 1);
            let word_starts = c.is_uppercase()
                && before.is_some_and(|b| {
                    b.is_lowercase()
                        || b.is_ascii_digit()
                        || (b.is_uppercase() && after.is_some_and(|a| a.is_lowercase()))
                });
            if word_starts {
                out.push('_');
            }
            out.extend(c.to_lowercase());
        }
        out
    }
}

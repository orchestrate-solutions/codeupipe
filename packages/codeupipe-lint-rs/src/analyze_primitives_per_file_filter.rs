use codeupipe::{Filter, StepError};

use crate::lint_run::LintRun;
use crate::primitive_kind::{is_test_file, primitives_in};
use crate::rules::{make_finding, ONE_PRIMITIVE_PER_FILE};

/// CUP-I005: one primitive in each file.
///
/// Flagged: each primitive at the top level of a file after the first. Not
/// flagged: plain types and functions beside the primitive, types in a
/// function or a module of the file, and the files of `tests/`.
///
/// Reads `sources`. Writes `findings`.
pub struct AnalyzePrimitivesPerFileFilter;

impl Filter<LintRun> for AnalyzePrimitivesPerFileFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        for source in run
            .sources
            .iter()
            .filter(|source| !is_test_file(&source.path))
        {
            let primitives = primitives_in(&source.tree.items);
            let Some((first, rest)) = primitives.split_first() else {
                continue;
            };
            for other in rest {
                let what = format!(
                    "{} `{}` shares this file with {} `{}`",
                    other.kind.name(),
                    other.name,
                    first.kind.name(),
                    first.name
                );
                let finding = make_finding(source, other.at, ONE_PRIMITIVE_PER_FILE, &what, None);
                run.findings.push(finding);
            }
        }
        Ok(())
    }
}

use codeupipe::{Filter, StepError};

use crate::finding::Finding;
use crate::lint_run::LintRun;
use crate::rules::{rule, MARKER_ALLOWS_NOTHING};

/// Finds each `cup: allow-...` comment that allowed no finding (CUP-I009, a
/// warning). Such a comment stays when the code that it was for is gone or
/// has moved, or when its kind has a spelling error.
///
/// Only a comment line that starts with the marker counts, so text that
/// names a marker in a string, a doc comment or the middle of a sentence is
/// not reported.
///
/// Reads `sources` and `used_markers` (from ApplySuppressionsFilter). Writes
/// `findings`.
pub struct AnalyzeStaleMarkersFilter;

impl Filter<LintRun> for AnalyzeStaleMarkersFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        let stale = rule(MARKER_ALLOWS_NOTHING).expect("a rule");
        for source in &run.sources {
            let unused = source.markers.iter().filter(|marker| {
                !run.used_markers
                    .iter()
                    .any(|(path, line)| *path == source.path && *line == marker.line)
            });
            for marker in unused {
                run.findings.push(Finding {
                    path: source.path.clone(),
                    line: marker.line,
                    col: marker.col,
                    rule: MARKER_ALLOWS_NOTHING.to_string(),
                    slug: stale.slug.to_string(),
                    message: format!(
                        "The comment `cup: {}` allows nothing. {}",
                        marker.kind, stale.fix
                    ),
                    call_line: None,
                    warning: true,
                });
            }
        }
        Ok(())
    }
}

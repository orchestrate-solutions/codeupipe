use std::collections::HashMap;

use codeupipe::{Filter, StepError};

use crate::lint_run::LintRun;
use crate::source::Marker;

/// The markers that allow a CUP-A finding.
const ANONYMOUS: &[&str] = &["allow-anonymous"];
/// The markers that allow a CUP-I finding.
const INVARIANT: &[&str] = &[
    "allow-state-read",
    "allow-shared-file",
    "allow-name",
    "allow-plain",
];

/// Drops the findings that a comment allows.
///
/// `// cup: allow-anonymous` allows a CUP-A finding. `// cup: allow-state-read`,
/// `allow-shared-file`, `allow-name` and `allow-plain` allow a CUP-I finding.
/// The comment is on the line of the finding, on the line of the `add_...`
/// call around it, or alone on the line directly above. Any text can follow
/// the marker.
///
/// Reads `findings` and `sources`. Writes `findings` (kept), `suppressed`
/// (dropped), and `used_markers` (each comment that allowed a finding).
pub struct ApplySuppressionsFilter;

impl Filter<LintRun> for ApplySuppressionsFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        let markers: HashMap<&str, &[Marker]> = run
            .sources
            .iter()
            .map(|source| (source.path.as_str(), source.markers.as_slice()))
            .collect();
        let mut kept = Vec::new();
        for finding in std::mem::take(&mut run.findings) {
            let kinds = if finding.rule.starts_with("CUP-A") {
                ANONYMOUS
            } else {
                INVARIANT
            };
            let file = markers
                .get(finding.path.as_str())
                .copied()
                .unwrap_or_default();
            let allows = |marker: &&Marker| {
                kinds.contains(&marker.kind.as_str())
                    && (marker.line == finding.line
                        || Some(marker.line) == finding.call_line
                        || (marker.alone && marker.line + 1 == finding.line))
            };
            let places: Vec<usize> = file
                .iter()
                .filter(allows)
                .map(|marker| marker.line)
                .collect();
            if places.is_empty() {
                kept.push(finding);
                continue;
            }
            for line in places {
                run.used_markers.push((finding.path.clone(), line));
            }
            run.suppressed.push(finding);
        }
        run.findings = kept;
        Ok(())
    }
}

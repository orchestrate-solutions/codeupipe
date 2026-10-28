use codeupipe::{Filter, StepError};

use crate::lint_run::LintRun;

/// The findings as sorted report lines, and the exit code.
///
/// Reads `findings`, `suppressed`, `errors` and `strict`. Writes `findings`
/// (sorted), `report` (text for stdout), `error_report` (text for stderr),
/// and `exit_code`: 0 no findings, 1 findings, 2 a path could not be read,
/// so the check is not complete.
///
/// A warning is in the report and is counted apart. It does not make the
/// exit code 1, unless the run is strict.
pub struct FormatReportFilter;

impl Filter<LintRun> for FormatReportFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        run.findings.sort_by(|a, b| {
            (&a.path, a.line, a.col, &a.rule).cmp(&(&b.path, b.line, b.col, &b.rule))
        });
        let warnings = run
            .findings
            .iter()
            .filter(|finding| finding.warning)
            .count();
        let real = run.findings.len() - warnings;
        let mut summary = match real {
            0 => "No findings".to_string(),
            1 => "1 finding".to_string(),
            _ => format!("{real} findings"),
        };
        if !run.suppressed.is_empty() {
            summary += &format!(" ({} suppressed)", run.suppressed.len());
        }
        summary += ".";
        match warnings {
            0 => {}
            1 => summary += " 1 warning.",
            _ => summary += &format!(" {warnings} warnings."),
        }
        let mut lines: Vec<String> = run
            .findings
            .iter()
            .map(|finding| finding.format())
            .collect();
        lines.push(summary);
        run.report = lines.join("\n");
        run.error_report = run
            .errors
            .iter()
            .map(|error| format!("error: {error}"))
            .collect::<Vec<_>>()
            .join("\n");
        let fails = real > 0 || (warnings > 0 && run.strict);
        run.exit_code = match (run.errors.is_empty(), fails) {
            (false, _) => 2,
            (true, true) => 1,
            (true, false) => 0,
        };
        Ok(())
    }
}

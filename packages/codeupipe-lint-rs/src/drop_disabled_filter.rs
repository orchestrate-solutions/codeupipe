use codeupipe::{Filter, StepError};

use crate::lint_run::LintRun;

/// Drops the findings of the rules that the project switched off, from those
/// that are reported and from those that a comment allowed.
///
/// Reads `disable`. Writes `findings` and `suppressed`.
pub struct DropDisabledFilter;

impl Filter<LintRun> for DropDisabledFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        let disable = &run.disable;
        run.findings
            .retain(|finding| !disable.contains(&finding.rule));
        run.suppressed
            .retain(|finding| !disable.contains(&finding.rule));
        Ok(())
    }
}

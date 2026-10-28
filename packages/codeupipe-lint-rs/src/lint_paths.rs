use codeupipe::{Pipeline, StepError};

use crate::lint_pipeline::LintPipeline;
use crate::lint_run::LintRun;

/// How a run is done: the files that are left out, the rules that are off,
/// and whether a warning fails the run.
#[derive(Clone, Debug, Default)]
pub struct LintOptions {
    pub exclude: Vec<String>,
    pub disable: Vec<String>,
    pub strict: bool,
}

/// Run the linter over `paths` (files or directories). The run that comes
/// back holds `findings`, `suppressed`, `errors`, `report`, `error_report`
/// and `exit_code`.
pub fn lint_paths(paths: &[String], options: &LintOptions) -> Result<LintRun, StepError> {
    Pipeline::named(LintPipeline).run(&LintRun {
        paths: paths.to_vec(),
        exclude: options.exclude.clone(),
        disable: options.disable.clone(),
        strict: options.strict,
        ..LintRun::default()
    })
}

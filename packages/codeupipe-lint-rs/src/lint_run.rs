use codeupipe::PipelineData;

use crate::finding::Finding;
use crate::source::Source;

/// What the lint pipeline carries from step to step: the input of a run,
/// and what each step adds.
#[derive(Clone, Default)]
pub struct LintRun {
    /// Files or directories to check.
    pub paths: Vec<String>,
    /// Globs matched against the path of each file; a match is not checked.
    pub exclude: Vec<String>,
    /// Rule ids that are switched off.
    pub disable: Vec<String>,
    /// A warning fails the run too.
    pub strict: bool,
    /// The Rust files under `paths` (CollectFilesFilter).
    pub files: Vec<String>,
    /// The files that parse (ParseFilesFilter).
    pub sources: Vec<Source>,
    /// The findings that are reported.
    pub findings: Vec<Finding>,
    /// The findings that a comment allowed (ApplySuppressionsFilter).
    pub suppressed: Vec<Finding>,
    /// Each comment that allowed a finding, as (path, line).
    pub used_markers: Vec<(String, usize)>,
    /// A path that could not be read: the check is not complete.
    pub errors: Vec<String>,
    /// The report for stdout (FormatReportFilter).
    pub report: String,
    /// The errors for stderr.
    pub error_report: String,
    /// 0 no findings, 1 findings, 2 a path could not be read.
    pub exit_code: i32,
}

impl PipelineData for LintRun {}

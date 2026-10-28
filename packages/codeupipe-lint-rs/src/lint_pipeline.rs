use codeupipe::{NamedPipeline, Pipeline};

use crate::analyze_plain_logic_filter::AnalyzePlainLogicFilter;
use crate::analyze_primitive_names_filter::AnalyzePrimitiveNamesFilter;
use crate::analyze_primitives_per_file_filter::AnalyzePrimitivesPerFileFilter;
use crate::analyze_stale_markers_filter::AnalyzeStaleMarkersFilter;
use crate::analyze_state_reads_filter::AnalyzeStateReadsFilter;
use crate::analyze_steps_filter::AnalyzeStepsFilter;
use crate::apply_suppressions_filter::ApplySuppressionsFilter;
use crate::collect_files_filter::CollectFilesFilter;
use crate::drop_disabled_filter::DropDisabledFilter;
use crate::format_report_filter::FormatReportFilter;
use crate::lint_run::LintRun;
use crate::parse_files_filter::ParseFilesFilter;

/// The linter, as a codeupipe pipeline: `Pipeline::named(LintPipeline)`.
pub struct LintPipeline;

impl NamedPipeline<LintRun> for LintPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline<LintRun>) {
        pipeline.add_filter(CollectFilesFilter); // paths to files
        pipeline.add_filter(ParseFilesFilter); // files to syntax trees (CUP-I000)
        pipeline.add_filter(AnalyzeStepsFilter); // CUP-A003, A005
        pipeline.add_filter(AnalyzeStateReadsFilter); // CUP-I003
        pipeline.add_filter(AnalyzePrimitivesPerFileFilter); // CUP-I005
        pipeline.add_filter(AnalyzePrimitiveNamesFilter); // CUP-I006, CUP-I007
        pipeline.add_filter(AnalyzePlainLogicFilter); // CUP-I008, a warning
        pipeline.add_filter(ApplySuppressionsFilter);
        pipeline.add_filter(AnalyzeStaleMarkersFilter); // CUP-I009, a warning
        pipeline.add_filter(DropDisabledFilter); // last, so that a comment for a rule that is off is not stale
        pipeline.add_filter(FormatReportFilter);
    }
}

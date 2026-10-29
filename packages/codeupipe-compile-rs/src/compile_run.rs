use codeupipe::PipelineData;

use crate::key_type::KeyType;
use crate::key_use::KeyUse;
use crate::lowered_step::LoweredStep;
use crate::source::Source;
use crate::step::StepPlan;

/// What the compile pipeline carries from step to step: the input, and what
/// each step adds.
#[derive(Clone, Default)]
pub struct CompileRun {
    /// Files or directories with the pipeline and its steps.
    pub paths: Vec<String>,
    /// The name of the type that implements `NamedPipeline`.
    pub pipeline: String,
    /// The parsed files (ReadSourcesFilter).
    pub sources: Vec<Source>,
    /// The name of the compiled struct: `PricingPipeline` gives `PricingData` (ResolvePipelineFilter).
    pub data: String,
    /// Each step, in the order of the pipeline (ResolvePipelineFilter).
    pub steps: Vec<StepPlan>,
    /// Each step as a plain function (LowerStepsFilter).
    pub functions: Vec<LoweredStep>,
    /// Each use of a key, in order (LowerStepsFilter).
    pub uses: Vec<KeyUse>,
    /// The `use` items of the step files that the functions need (LowerStepsFilter).
    pub imports: Vec<syn::ItemUse>,
    /// Each key with its field and its type, in the order of first use (TypeKeysFilter).
    pub keys: Vec<(String, String, KeyType)>,
    /// The compiled module (EmitModuleFilter).
    pub module: String,
}

impl PipelineData for CompileRun {}

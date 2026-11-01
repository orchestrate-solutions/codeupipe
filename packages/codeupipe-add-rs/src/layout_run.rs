use codeupipe::PipelineData;

use crate::laid_out::LaidOut;
use crate::layout_value::LayoutValue;

/// What the layout pipeline carries from step to step: the file, its
/// components, and what the command did.
#[derive(Clone, Debug, Default)]
pub struct LayoutRun {
    /// The root of the project: the directory where the command runs.
    pub root: String,
    /// The layout file, relative to the root.
    pub layout_path: String,
    /// The file, as data (ReadLayoutFilter).
    pub layout: Option<LayoutValue>,
    /// The directory of the component files: `root:` of the layout, or `src`.
    pub directory: String,
    /// The components, in the order of the file.
    pub components: Vec<LaidOut>,
    /// The lines that the crate needs, each once, in order, as the command
    /// prints them on stderr.
    pub module_notes: Vec<String>,
    /// The files that the command wrote, component first (WriteLayoutFilter).
    pub written: Vec<String>,
    /// The files that were there already, and that the command kept.
    pub kept: Vec<String>,
    /// The kept pipeline files whose steps are not those of the layout.
    pub stale: Vec<String>,
}

impl PipelineData for LayoutRun {}

use crate::layout_step::LayoutStep;

/// One component of a layout: what the file says, and what each step adds.
#[derive(Clone, Debug, Default)]
pub struct LaidOut {
    /// `filter`, `predicate`, `tap`, `hook` or `pipeline`.
    pub kind: String,
    /// The name in the layout: `Discount`.
    pub name: String,
    /// What the component does, for its header comment.
    pub description: String,
    /// Only for a pipeline: its steps, in order.
    pub steps: Vec<LayoutStep>,
    /// Only for a pipeline: the names of its hooks.
    pub hooks: Vec<String>,
    /// The type name of phase 1: `DiscountFilter` (NameComponentsFilter).
    pub type_name: String,
    /// The file name, without its directory: `discount_filter`.
    pub snake: String,
    /// The component file, relative to the root.
    pub component_path: String,
    /// The test file, relative to the root.
    pub test_path: String,
    /// The path of the module in the crate: `pricing::discount_filter`.
    pub module: String,
    /// The calls of a pipeline, steps first, then hooks: the method and the
    /// type names in it (ResolveStepsFilter).
    pub calls: Vec<(String, Vec<String>)>,
    /// The `use` of each step: the module and the type, sorted.
    pub uses: Vec<(String, String)>,
    /// The text of the component file (RenderLayoutFilter).
    pub component_text: String,
    /// The text of the test file (RenderLayoutFilter).
    pub test_text: String,
}

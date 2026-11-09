use codeupipe::PipelineData;

/// What the `add` pipeline carries from step to step: the arguments of the
/// command, and what each step adds.
#[derive(Clone, Debug, Default)]
pub struct AddRun {
    /// The root of the project: the directory where the command runs.
    pub root: String,
    /// What to make: `filter`, `predicate`, `tap`, `hook` or `pipeline`.
    pub kind: String,
    /// The name that was given: `Discount`, `at_least` or `audit-log`.
    pub name: String,
    /// The directory of the component file, relative to `root`. The default
    /// is `src`, the Rust default of the contract.
    pub directory: String,
    /// What the component does, for its header comment. Empty says so.
    pub description: String,
    /// The name of the component file, without its directory (`discount_filter`).
    pub snake: String,
    /// The name that the component file declares (`DiscountFilter`).
    pub type_name: String,
    /// The component file, relative to the root (`src/discount_filter.rs`).
    pub component_path: String,
    /// The test file, relative to the root (`tests/discount_filter.rs`).
    pub test_path: String,
    /// The name of the crate, from `Cargo.toml`, that the test imports. An
    /// empty name means the command could not read it, and no `use` line.
    pub crate_name: String,
    /// The text of the component file (RenderFilesFilter).
    pub component_text: String,
    /// The text of the test file (RenderFilesFilter).
    pub test_text: String,
    /// The notes that the command writes on stderr, each a line to add to a
    /// file of the crate, in the order in which they are needed.
    pub module_notes: Vec<String>,
    /// The file of a component directory of its own (`src/pricing.rs`). Empty
    /// when the component is in `src` itself, or in the root.
    pub directory_module_path: String,
    /// The files that the command made, component first (WriteFilesFilter).
    pub written: Vec<String>,
    /// Only for a pipeline of a layout: the method and the type names of
    /// each call. With calls, RenderFilesFilter writes the steps.
    pub calls: Vec<(String, Vec<String>)>,
    /// Only for a pipeline of a layout: the module and the type of each step.
    pub uses: Vec<(String, String)>,
}

impl PipelineData for AddRun {}

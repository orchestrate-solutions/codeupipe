//! A linter for Rust code that uses codeupipe. It reads the source and does
//! not run it.
//!
//! The linter is a codeupipe pipeline ([`LintPipeline`]) that carries a type
//! of its own, [`LintRun`], in place of a `Payload`: a run holds syntax
//! trees, which are not JSON-shaped values.
//!
//! ```no_run
//! use codeupipe_lint::{lint_paths, LintOptions};
//!
//! let out = lint_paths(&["src".to_string()], &LintOptions::default())?;
//! println!("{}", out.report);
//! # Ok::<(), codeupipe::StepError>(())
//! ```

mod analyze_plain_logic_filter;
mod analyze_primitive_names_filter;
mod analyze_primitives_per_file_filter;
mod analyze_stale_markers_filter;
mod analyze_state_reads_filter;
mod analyze_steps_filter;
mod apply_suppressions_filter;
mod collect_files_filter;
mod drop_disabled_filter;
mod finding;
mod fnmatch;
mod format_report_filter;
mod lint_paths;
mod lint_pipeline;
mod lint_run;
mod logic;
mod markers;
mod parse_files_filter;
mod primitive_kind;
mod read_config;
mod rules;
mod source;
mod step_visitor;

pub use finding::Finding;
pub use lint_paths::{lint_paths, LintOptions};
pub use lint_pipeline::LintPipeline;
pub use lint_run::LintRun;
pub use read_config::{read_lint_config, LintConfig, CONFIG_NAME};
pub use rules::{Rule, RULES};
pub use source::{Marker, Source};

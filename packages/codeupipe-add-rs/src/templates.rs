// The text of the two files that `add` makes, in the form of Rust.
//
// `{type_name}`, `{description}`, `{crate_name}`, `{module}` and `{snake}`
// are filled in by RenderFilesFilter. Each component does nothing
// (conformance/ADD.md), and the test fails on purpose, with the message of
// the contract.

/// The component file of a Filter: it returns the Payload with no change.
pub const FILTER: &str = r#"//! {type_name}: {description}

use codeupipe::{Filter, Payload, StepError};

pub struct {type_name};

impl Filter for {type_name} {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let _ = payload;
        Ok(())
    }
}
"#;

/// The component file of a Predicate: its answer is always no.
pub const PREDICATE: &str = r#"//! {type_name}: {description}

use codeupipe::{Payload, Predicate};

pub struct {type_name};

impl Predicate for {type_name} {
    fn test(&self, payload: &Payload) -> bool {
        let _ = payload;
        false
    }
}
"#;

/// The component file of a Tap: it reads the data and writes nothing.
pub const TAP: &str = r#"//! {type_name}: {description}

use codeupipe::{Payload, StepError, Tap};

pub struct {type_name};

impl Tap for {type_name} {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        let _ = payload;
        Ok(())
    }
}
"#;

/// The component file of a Hook: it does nothing at each event. The default
/// methods of the trait already do nothing, so the impl is empty.
pub const HOOK: &str = r#"//! {type_name}: {description}

use codeupipe::Hook;

pub struct {type_name};

impl Hook for {type_name} {}
"#;

/// The component file of a named Pipeline with no steps.
pub const PIPELINE: &str = r#"//! {type_name}: {description}

use codeupipe::{NamedPipeline, Pipeline};

pub struct {type_name};

impl NamedPipeline for {type_name} {
    fn add_steps(&self, _pipeline: &mut Pipeline) {}
}
"#;

/// The test file: one test that makes the component and fails with the
/// message of the contract, so that the work starts at RED.
pub const TEST: &str = r#"//! The acceptance case of {type_name}.

use {crate_name}::{module}::{type_name};

#[test]
fn {snake}_does_nothing_yet() {{
    let component = {type_name};
    let _ = component;
    panic!("Write the acceptance case for {type_name}.");
}}
"#;

/// The line that a user adds to the file that holds the modules, so that the
/// new file becomes part of the crate.
pub const MODULE_LINE: &str = "pub mod {snake};";

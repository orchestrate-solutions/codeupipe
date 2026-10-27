//! codeupipe: the eight primitives.
//!
//! Payload, Filter, Predicate, Valve, Tap, Hook, State and Pipeline, as the
//! contract (conformance/API.md) defines them. A Valve is added with
//! `pipeline.add_valve(predicate, filter)`; its type is not a public name.
//!
//! ```
//! use codeupipe::{Filter, Map, Payload, Pipeline, StepError, Value};
//!
//! struct GreetFilter;
//!
//! impl Filter for GreetFilter {
//!     fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
//!         let name = payload.get("name").and_then(Value::as_str).unwrap_or("World").to_string();
//!         payload.insert("greeting", format!("Hello, {name}!"));
//!         Ok(())
//!     }
//! }
//!
//! let mut pipeline = Pipeline::new();
//! pipeline.add_filter(GreetFilter);
//! let out = pipeline.run(&Payload::from_map(Map::from([("name", "Ada")])))?;
//! assert_eq!(out.get("greeting"), Some(&Value::from("Hello, Ada!")));
//! assert_eq!(pipeline.state().executed(), ["GreetFilter"]);
//! # Ok::<(), StepError>(())
//! ```
//!
//! # What the type system refuses
//!
//! The contract refuses a step without the method of its role when it is
//! added. In Rust that is a compile error.
//!
//! A function is not a step:
//!
//! ```compile_fail
//! use codeupipe::{Payload, Pipeline, StepError};
//! let mut pipeline = Pipeline::new();
//! pipeline.add_filter(|_payload: &mut Payload| -> Result<(), StepError> { Ok(()) });
//! ```
//!
//! The condition of a Valve comes first:
//!
//! ```compile_fail
//! use codeupipe::{Filter, Payload, Pipeline, Predicate, StepError};
//! struct OnPredicate;
//! impl Predicate for OnPredicate {
//!     fn test(&self, _payload: &Payload) -> bool { true }
//! }
//! struct SetFilter;
//! impl Filter for SetFilter {
//!     fn call(&self, _payload: &mut Payload) -> Result<(), StepError> { Ok(()) }
//! }
//! let mut pipeline = Pipeline::new();
//! pipeline.add_valve(SetFilter, OnPredicate);
//! ```
//!
//! Only a Filter writes. A Tap gets `&Payload`:
//!
//! ```compile_fail
//! use codeupipe::{Payload, StepError, Tap};
//! struct WritingTap;
//! impl Tap for WritingTap {
//!     fn observe(&self, payload: &Payload) -> Result<(), StepError> {
//!         payload.insert("seen", true);
//!         Ok(())
//!     }
//! }
//! ```

mod filter;
mod hook;
mod map;
mod named_pipeline;
mod payload;
mod pipeline;
mod predicate;
mod state;
mod step_error;
mod step_label;
mod tap;
mod value;
mod valve;

pub use filter::Filter;
pub use hook::Hook;
pub use map::Map;
pub use named_pipeline::NamedPipeline;
pub use payload::Payload;
pub use pipeline::Pipeline;
pub use predicate::Predicate;
pub use state::State;
pub use step_error::StepError;
pub use tap::Tap;
pub use value::Value;

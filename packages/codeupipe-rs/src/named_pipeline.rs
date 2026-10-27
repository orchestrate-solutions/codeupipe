use crate::pipeline::Pipeline;

/// A pipeline with a name: a type that adds the steps.
///
/// `Pipeline::named(UserOnboarding)` makes the pipeline, and its label is
/// `UserOnboarding`. Rust has no class to extend, so this trait is the named
/// type of the contract (`class UserOnboarding(Pipeline)` in Python).
/// `add_steps` only adds steps.
pub trait NamedPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline);
}

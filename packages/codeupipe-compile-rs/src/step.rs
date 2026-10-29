use syn::Expr;

use crate::place::Place;

/// The role of a step: what its method is.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role {
    Filter,
    Predicate,
    Tap,
}

/// One step as the pipeline makes it: its type, and each setting with the
/// literal that the pipeline gives it.
#[derive(Clone)]
pub struct Step {
    pub role: Role,
    pub type_name: String,
    pub settings: Vec<(String, Expr)>,
    pub place: Place,
}

/// One `add_...` call of the pipeline.
#[derive(Clone)]
pub enum StepPlan {
    Filter(Step),
    /// The Predicate, then the Filter.
    Valve(Step, Step),
    Tap(Step),
}

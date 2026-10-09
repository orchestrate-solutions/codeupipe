//! Parallel: a fan-out/fan-in group, built one concrete filter at a time so
//! each member keeps its identity: `parallel[<member identities>]`.

use crate::filter::Filter;
use crate::step_identity::identify;

#[derive(Default)]
pub struct Parallel {
    pub(crate) filters: Vec<Box<dyn Filter>>,
    pub(crate) members: Vec<String>,
}

impl Parallel {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a member filter.
    pub fn with<F: Filter + 'static>(mut self, filter: F) -> Self {
        self.members.push(identify::<F>("Filter"));
        self.filters.push(Box::new(filter));
        self
    }
}

use codeupipe::{Filter, StepError};

use crate::order::Order;

/// A Filter.
pub struct MarkBulkFilter;

impl Filter<Order> for MarkBulkFilter {
    fn call(&self, order: &mut Order) -> Result<(), StepError> {
        order.bulk = true;
        Ok(())
    }
}

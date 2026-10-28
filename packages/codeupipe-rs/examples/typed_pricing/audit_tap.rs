use codeupipe::{StepError, Tap};

use crate::order::Order;

/// A Tap: reads the Order and returns nothing. If it fails, State records
/// the error and the run goes on.
pub struct AuditTap;

impl Tap<Order> for AuditTap {
    fn observe(&self, order: &Order) -> Result<(), StepError> {
        println!("audit: {order:?}");
        Ok(())
    }
}

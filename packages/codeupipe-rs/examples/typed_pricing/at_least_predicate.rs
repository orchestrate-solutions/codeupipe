use codeupipe::Predicate;

use crate::order::Order;

/// A Predicate: asks a yes-or-no question and changes nothing. Its setting
/// is on the instance.
pub struct AtLeastPredicate {
    minimum: u32,
}

impl AtLeastPredicate {
    pub fn new(minimum: u32) -> Self {
        AtLeastPredicate { minimum }
    }
}

impl Predicate<Order> for AtLeastPredicate {
    fn test(&self, order: &Order) -> bool {
        order.qty >= self.minimum
    }
}

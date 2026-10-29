use codeupipe::{Payload, Predicate};

/// True when the guest is a VIP.
pub struct VipPredicate;

impl Predicate for VipPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.has("vip")
    }
}

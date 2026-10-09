#![allow(dead_code)] // each test binary uses a subset
// Shared test filters (included by the integration tests below).
use codeupipe_core::{Filter, Payload, Tap, Value};

pub type BoxError = Box<dyn std::error::Error + Send + Sync>;

pub struct Set(pub &'static str, pub i64);
impl Filter for Set {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        Ok(p.insert(self.0, Value::Int(self.1)))
    }
}

pub struct Add(pub &'static str, pub i64);
impl Filter for Add {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let current = p.get(self.0).and_then(Value::as_int).unwrap_or(0);
        Ok(p.insert(self.0, Value::Int(current + self.1)))
    }
}

pub struct PanickingTap;
impl Tap for PanickingTap {
    fn observe(&self, _: &Payload) {
        panic!("sink down");
    }
}

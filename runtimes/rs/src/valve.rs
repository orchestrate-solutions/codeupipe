//! Valve: Conditional Flow Control
//!
//! A Valve wraps a Filter with a predicate — the inner filter only
//! executes when the predicate evaluates to true.
//!
//! See also: TypeScript, Python, Go, C# implementations.

use crate::filter::Filter;
use crate::payload::Payload;
use crate::predicate::Predicate;
use crate::step_identity::identify;
use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};

/// Conditional flow control — gates a Filter with a predicate.
///
/// Identified by its inner filter (conformance/API.md, "Step identity"). The
/// predicate is an object: a named type implementing [`Predicate`].
pub struct Valve {
    inner_identity: String,
    predicate_symbol: String,
    inner: Box<dyn Filter>,
    predicate: Box<dyn Predicate>,
    last_skipped: AtomicBool,
}

impl Valve {
    pub fn new<F, P>(inner: F, predicate: P) -> Self
    where
        F: Filter + 'static,
        P: Predicate + 'static,
    {
        Valve {
            inner_identity: identify::<F>("Filter"),
            predicate_symbol: identify::<P>("Valve predicate"),
            inner: Box::new(inner),
            predicate: Box::new(predicate),
            last_skipped: AtomicBool::new(false),
        }
    }

    /// The inner filter's identity: the Valve's identity as a step.
    pub fn inner_identity(&self) -> &str {
        &self.inner_identity
    }

    /// The predicate's identity (detail).
    pub fn predicate_symbol(&self) -> &str {
        &self.predicate_symbol
    }

    /// Whether the last call was skipped.
    pub fn last_skipped(&self) -> bool {
        self.last_skipped.load(Ordering::Relaxed)
    }
}

impl Filter for Valve {
    fn call(&self, payload: Payload) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
        if self.predicate.test(&payload) {
            self.last_skipped.store(false, Ordering::Relaxed);
            self.inner.call(payload)
        } else {
            self.last_skipped.store(true, Ordering::Relaxed);
            Ok(payload)
        }
    }

    fn last_skipped(&self) -> bool {
        self.last_skipped.load(Ordering::Relaxed)
    }
}

impl fmt::Display for Valve {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Valve({}, {})", self.inner_identity, self.predicate_symbol)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::payload::Value;

    struct DoubleX;
    impl Filter for DoubleX {
        fn call(
            &self,
            payload: Payload,
        ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
            let x = payload.get("x").and_then(|v| v.as_int()).unwrap_or(0);
            Ok(payload.insert("x", Value::Int(x * 2)))
        }
    }

    struct Positive;
    impl crate::predicate::Predicate for Positive {
        fn test(&self, p: &Payload) -> bool {
            p.get("x").and_then(|v| v.as_int()).unwrap_or(0) > 0
        }
    }

    struct Always;
    impl crate::predicate::Predicate for Always {
        fn test(&self, _: &Payload) -> bool {
            true
        }
    }

    #[test]
    fn executes_when_predicate_true() {
        let valve = Valve::new(DoubleX, Positive);
        let result = valve
            .call(Payload::new().insert("x", Value::Int(5)))
            .unwrap();
        assert_eq!(result.get("x").unwrap().as_int(), Some(10));
    }

    #[test]
    fn skips_when_predicate_false() {
        let valve = Valve::new(DoubleX, Positive);
        let result = valve
            .call(Payload::new().insert("x", Value::Int(-1)))
            .unwrap();
        assert_eq!(result.get("x").unwrap().as_int(), Some(-1));
        assert!(valve.last_skipped());
    }

    #[test]
    fn display() {
        let valve = Valve::new(DoubleX, Always);
        let s = format!("{}", valve);
        assert!(s.contains("DoubleX") && s.contains("Always"), "{s}");
    }
}

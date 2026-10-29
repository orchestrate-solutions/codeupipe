use std::fmt;

use crate::place::Place;

/// A pipeline that the compiler does not compile, with the place and the
/// fix. Code that compiles gives the output of the pipeline; a shape for
/// which the compiler cannot keep that rule is refused.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Refusal {
    pub place: Place,
    pub what: String,
    pub fix: String,
}

impl Refusal {
    pub fn new(place: Place, what: impl Into<String>, fix: impl Into<String>) -> Refusal {
        Refusal {
            place,
            what: what.into(),
            fix: fix.into(),
        }
    }
}

impl fmt::Display for Refusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let Place { path, line, col } = &self.place;
        write!(f, "{path}:{line}:{col}  {}. {}", self.what, self.fix)
    }
}

impl std::error::Error for Refusal {}

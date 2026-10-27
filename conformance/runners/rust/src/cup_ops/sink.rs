//! Where the Taps of the runner record what they see. The runner empties it
//! before each case.
use std::cell::RefCell;

use codeupipe::Value;

thread_local! {
    static TAPS: RefCell<Vec<Value>> = const { RefCell::new(Vec::new()) };
}

pub fn record(value: Value) {
    TAPS.with(|taps| taps.borrow_mut().push(value));
}

/// What was recorded since the last call, and an empty log.
pub fn take() -> Vec<Value> {
    TAPS.with(|taps| taps.take())
}

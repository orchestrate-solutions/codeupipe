//! Where the steps of the runner record what they see, and the hook for
//! running the pipeline of a case again. The runner empties it before each
//! case.
use std::cell::RefCell;
use std::rc::Rc;

use codeupipe::{Map, State, StepError, Value};

/// Runs the pipeline of the case again, with this input and a new State.
pub type RunAgain = Rc<dyn Fn(Map) -> Result<(), StepError>>;

thread_local! {
    static TAPS: RefCell<Vec<Value>> = const { RefCell::new(Vec::new()) };
    static RUN_AGAIN: RefCell<Option<RunAgain>> = const { RefCell::new(None) };
    static INNER_STATES: RefCell<Vec<State>> = const { RefCell::new(Vec::new()) };
}

pub fn record(value: Value) {
    TAPS.with(|taps| taps.borrow_mut().push(value));
}

/// What was recorded since the last call, and an empty log.
pub fn take() -> Vec<Value> {
    TAPS.with(|taps| taps.take())
}

/// How the `run_again` step of this case runs its pipeline again.
pub fn set_run_again(run_again: Option<RunAgain>) {
    RUN_AGAIN.with(|slot| slot.replace(run_again));
}

pub fn run_again(input: Map) -> Result<(), StepError> {
    // Taken out of the cell first: the run that it starts reads the cell too.
    let run_again = RUN_AGAIN.with(|slot| slot.borrow().clone());
    match run_again {
        Some(run_again) => run_again(input),
        None => Err("no pipeline to run again".into()),
    }
}

/// Keep the State of a run that a `run_again` step started.
pub fn keep_inner_state(state: State) {
    INNER_STATES.with(|states| states.borrow_mut().push(state));
}

/// The States kept since the last call, and an empty list.
pub fn take_inner_states() -> Vec<State> {
    INNER_STATES.with(|states| states.take())
}

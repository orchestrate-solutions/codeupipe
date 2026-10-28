use codeupipe::{Hook, Payload};

/// A Hook: sees the lifecycle. `step` is the label of the step, which is the
/// name of its type. It is `None` for the pipeline itself.
pub struct PrintStepsHook;

impl Hook for PrintStepsHook {
    fn before(&self, step: Option<&str>, _payload: &Payload) {
        if let Some(step) = step {
            println!("  {step}");
        }
    }
}

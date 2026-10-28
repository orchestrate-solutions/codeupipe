/// The error of a step that fails. Any error type converts into it, and so
/// does text: `Err("sink is down".into())`.
pub type StepError = Box<dyn std::error::Error + Send + Sync>;

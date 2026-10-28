use codeupipe::Hook;

/// A Hook that does nothing: the cost of having one.
pub struct NoopHook;

impl Hook for NoopHook {}

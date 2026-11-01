use std::fmt;

/// The command cannot do what it was asked, and writes nothing.
///
/// `exit_code` is 1 when a file exists, and 2 when the arguments cannot be
/// used (conformance/ADD.md, "What the command prints, and its exit code").
#[derive(Clone, Debug)]
pub struct Refusal {
    pub exit_code: u8,
    pub message: String,
}

impl Refusal {
    /// A refusal with the exit code of the contract and the message for stderr.
    pub fn new(exit_code: u8, message: impl Into<String>) -> Self {
        Refusal {
            exit_code,
            message: message.into(),
        }
    }

    /// A file that is there already stops the run (exit 1), and its name is
    /// in the message with the word `exists`.
    pub fn exists(path: &str) -> Self {
        Self::new(1, format!("{path} exists"))
    }

    /// The arguments cannot be used (exit 2).
    pub fn usage(message: impl Into<String>) -> Self {
        Self::new(2, message)
    }
}

impl fmt::Display for Refusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for Refusal {}

/// One finding, at `path:line:col` (line and column start at 1).
///
/// `call_line` is the line of the `add_...` call around the finding, when it
/// is a different line: a comment that suppresses can be on that line too.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Finding {
    pub path: String,
    pub line: usize,
    pub col: usize,
    pub rule: String,
    pub slug: String,
    pub message: String,
    pub call_line: Option<usize>,
    /// A warning is reported and does not fail the run, unless the run is strict.
    pub warning: bool,
}

// cup: allow-plain the text of one finding, for the report
impl Finding {
    /// `path:line:col  RULE slug  message`, with `warning: ` before the message of a warning.
    pub fn format(&self) -> String {
        let warning = if self.warning { "warning: " } else { "" };
        format!(
            "{}:{}:{}  {} {}  {}{}",
            self.path, self.line, self.col, self.rule, self.slug, warning, self.message
        )
    }
}

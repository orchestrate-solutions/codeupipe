use proc_macro2::Span;

/// Where a refusal points: a file, a line and a column, from 1.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Place {
    pub path: String,
    pub line: usize,
    pub col: usize,
}

impl Place {
    pub fn of(path: &str, span: Span) -> Place {
        let start = span.start();
        Place {
            path: path.to_string(),
            line: start.line,
            col: start.column + 1,
        }
    }
}

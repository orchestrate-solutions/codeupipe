use proc_macro2::Span;

/// One parsed file.
#[derive(Clone)]
pub struct Source {
    pub path: String,
    pub text: String,
    pub tree: syn::File,
    /// The `cup: allow-...` comments of the file.
    pub markers: Vec<Marker>,
}

/// A comment line that starts with `cup: allow-...`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Marker {
    pub line: usize,
    pub col: usize,
    /// `allow-plain`, `allow-name`, ...: the word after `cup:`.
    pub kind: String,
    /// The line holds the comment and no code.
    pub alone: bool,
}

/// The line and column where `span` starts, from 1.
pub fn position(span: Span) -> (usize, usize) {
    let start = span.start();
    (start.line, start.column + 1)
}

/// The text of `span` in `text`. The lines of a span over several lines are
/// joined with their indent taken away: `self.pipeline.state()`.
// cup: allow-plain shared by the analysis Filters: the text of a node, for a message
pub fn text_of(text: &str, span: Span) -> String {
    let (start, end) = (span.start(), span.end());
    text.lines()
        .enumerate()
        .skip(start.line - 1)
        .take(end.line + 1 - start.line)
        .map(|(index, line)| {
            let to = (index + 1 == end.line).then_some(end.column);
            let from = (index + 1 == start.line).then_some(start.column);
            let taken: String = line
                .chars()
                .take(to.unwrap_or(usize::MAX))
                .skip(from.unwrap_or(0))
                .collect();
            match from {
                Some(_) => taken,
                None => taken.trim_start().to_string(),
            }
        })
        .collect()
}

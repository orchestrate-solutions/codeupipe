//! The `cup: allow-...` comments of a file.
//!
//! A syntax tree has no comments, so they are found between the tokens: the
//! text between two tokens is space and comments only. A doc comment is a
//! token (an attribute), so text in it is documentation, not a marker, and
//! so is text in a string.

use proc_macro2::{LineColumn, TokenStream, TokenTree};

use crate::source::Marker;

/// Each line of a comment of `text` that starts with `cup: allow-...`.
// cup: allow-plain used by the parse Filter: it finds the comments of a file, which a syntax tree does not keep
pub fn markers_of(text: &str) -> Vec<Marker> {
    let Ok(tokens) = text.parse::<TokenStream>() else {
        return Vec::new();
    };
    let lines = Lines::new(text);
    let mut taken = Vec::new();
    spans_of(tokens, &mut taken);
    let mut taken: Vec<(usize, usize)> = taken
        .into_iter()
        .map(|(start, end)| (lines.offset(start), lines.offset(end)))
        .collect();
    taken.sort_unstable();
    let mut markers = Vec::new();
    let mut at = 0;
    for (start, end) in taken {
        comments_in(text, &lines, at, start, &mut markers);
        at = at.max(end);
    }
    comments_in(text, &lines, at, text.len(), &mut markers);
    markers
}

/// Where each token starts and ends.
// cup: allow-plain used by the parse Filter: it finds the comments of a file, which a syntax tree does not keep
fn spans_of(tokens: TokenStream, out: &mut Vec<(LineColumn, LineColumn)>) {
    for token in tokens {
        if let TokenTree::Group(group) = &token {
            out.push((group.span_open().start(), group.span_open().end()));
            out.push((group.span_close().start(), group.span_close().end()));
            spans_of(group.stream(), out);
        } else {
            out.push((token.span().start(), token.span().end()));
        }
    }
}

/// The comments in `text[from..to]`, text that holds space and comments only.
// cup: allow-plain used by the parse Filter: it finds the comments of a file, which a syntax tree does not keep
fn comments_in(text: &str, lines: &Lines, from: usize, to: usize, out: &mut Vec<Marker>) {
    let mut at = from;
    while at < to {
        let rest = &text[at..to];
        let end = if rest.starts_with("//") {
            at + rest.find('\n').unwrap_or(rest.len())
        } else if rest.starts_with("/*") {
            at + block_comment_length(rest)
        } else {
            at += rest.chars().next().map_or(1, char::len_utf8);
            continue;
        };
        markers_in_comment(text, lines, at, end, out);
        at = end;
    }
}

/// The length of the block comment at the start of `text`. Block comments nest.
// cup: allow-plain used by the parse Filter: it finds the comments of a file, which a syntax tree does not keep
fn block_comment_length(text: &str) -> usize {
    let mut depth = 0;
    let mut at = 0;
    while at < text.len() {
        let rest = &text[at..];
        if rest.starts_with("/*") {
            depth += 1;
            at += 2;
        } else if rest.starts_with("*/") {
            depth -= 1;
            at += 2;
            if depth == 0 {
                return at;
            }
        } else {
            at += rest.chars().next().map_or(1, char::len_utf8);
        }
    }
    text.len()
}

/// Each line of the comment `text[from..to]` that starts with a marker.
// cup: allow-plain used by the parse Filter: it finds the comments of a file, which a syntax tree does not keep
fn markers_in_comment(text: &str, lines: &Lines, from: usize, to: usize, out: &mut Vec<Marker>) {
    let mut at = from;
    for (index, piece) in text[from..to].split('\n').enumerate() {
        let line = lines.line_of(at);
        let line_start = lines.starts[line - 1];
        let lead = piece.len() - strip_comment_lead(piece).len();
        if let Some(kind) = marker_kind(&piece[lead..]) {
            out.push(Marker {
                line,
                col: text[line_start..at + lead].chars().count() + 1,
                kind,
                // The first line of the comment may have code before it.
                alone: index > 0 || text[line_start..at].trim().is_empty(),
            });
        }
        at += piece.len() + 1;
    }
}

/// `piece` without the space and the comment characters at its start: `//`,
/// `/*`, or the `*` of a line inside a block comment.
// cup: allow-plain used by the parse Filter: it finds the comments of a file, which a syntax tree does not keep
fn strip_comment_lead(piece: &str) -> &str {
    let piece = piece.trim_start();
    let piece = if piece.starts_with("//") {
        piece.trim_start_matches('/')
    } else if let Some(rest) = piece.strip_prefix("/*") {
        rest.trim_start_matches('*')
    } else if piece.starts_with('*') && !piece.starts_with("*/") {
        &piece[1..]
    } else {
        piece
    };
    piece.trim_start()
}

/// `allow-plain` for `cup: allow-plain the reason`.
fn marker_kind(text: &str) -> Option<String> {
    let rest = text.strip_prefix("cup:")?.trim_start();
    rest.starts_with("allow-").then(|| {
        rest.chars()
            .take_while(|c| c.is_alphanumeric() || *c == '_' || *c == '-')
            .collect()
    })
}

/// The byte offset where each line of a text starts.
struct Lines<'a> {
    text: &'a str,
    starts: Vec<usize>,
}

impl<'a> Lines<'a> {
    fn new(text: &'a str) -> Self {
        let breaks = text.match_indices('\n').map(|(at, _)| at + 1);
        Lines {
            text,
            starts: std::iter::once(0).chain(breaks).collect(),
        }
    }

    /// The byte offset of a line (from 1) and column (from 0, in characters).
    fn offset(&self, at: LineColumn) -> usize {
        let start = self.starts[at.line - 1];
        start
            + self.text[start..]
                .char_indices()
                .nth(at.column)
                .map_or(self.text.len() - start, |(index, _)| index)
    }

    /// The line (from 1) of a byte offset.
    fn line_of(&self, offset: usize) -> usize {
        self.starts.partition_point(|start| *start <= offset)
    }
}

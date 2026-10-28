/// Whether `path` matches `pattern`, with the rules of a shell glob as
/// Python's fnmatch has them: `*` is any text (a `/` too), `?` is one
/// character, `[abc]` is one of the characters, `[a-z]` a range, and `[!a]`
/// any character but those.
pub fn fnmatch(path: &str, pattern: &str) -> bool {
    let path: Vec<char> = path.chars().collect();
    let pattern: Vec<char> = pattern.chars().collect();
    matches(&path, &pattern)
}

// cup: allow-plain shared by the collect Filter and its tests: a glob match, as Python's fnmatch has it
fn matches(path: &[char], pattern: &[char]) -> bool {
    match pattern.split_first() {
        None => path.is_empty(),
        Some(('*', rest)) => (0..=path.len()).any(|skip| matches(&path[skip..], rest)),
        Some(('?', rest)) => !path.is_empty() && matches(&path[1..], rest),
        Some(('[', rest)) => match (path.split_first(), rest.iter().position(|c| *c == ']')) {
            (Some((c, path_rest)), Some(end)) => {
                let (negated, class) = match rest[..end].split_first() {
                    Some(('!', class)) => (true, class),
                    _ => (false, &rest[..end]),
                };
                in_class(*c, class) != negated && matches(path_rest, &rest[end + 1..])
            }
            (Some((c, path_rest)), None) => *c == '[' && matches(path_rest, rest),
            (None, _) => false,
        },
        Some((p, rest)) => path.first() == Some(p) && matches(&path[1..], rest),
    }
}

// cup: allow-plain shared by the collect Filter and its tests: a glob match, as Python's fnmatch has it
fn in_class(c: char, class: &[char]) -> bool {
    let mut at = 0;
    while at < class.len() {
        if at + 2 < class.len() && class[at + 1] == '-' {
            if class[at] <= c && c <= class[at + 2] {
                return true;
            }
            at += 3;
        } else {
            if class[at] == c {
                return true;
            }
            at += 1;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::fnmatch;

    #[test]
    fn matches_as_a_shell_glob() {
        assert!(fnmatch("src/generated/x.rs", "*/generated/*"));
        assert!(fnmatch("a/b.rs", "*.rs"));
        assert!(!fnmatch("a/b.rs", "*.ts"));
        assert!(fnmatch("x1.rs", "x?.rs"));
        assert!(fnmatch("xb.rs", "x[abc].rs"));
        assert!(!fnmatch("xd.rs", "x[abc].rs"));
        assert!(fnmatch("xd.rs", "x[!abc].rs"));
        assert!(fnmatch("x5.rs", "x[0-9].rs"));
        assert!(fnmatch("x[.rs", "x[.rs"));
        assert!(!fnmatch("discount.rs", "*/discount.rs"));
    }
}

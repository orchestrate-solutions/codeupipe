use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::refusal::Refusal;

/// The role word that each kind adds to its type name.
const ROLES: [(&str, &str); 5] = [
    ("filter", "Filter"),
    ("predicate", "Predicate"),
    ("tap", "Tap"),
    ("hook", "Hook"),
    ("pipeline", "Pipeline"),
];

/// The kinds that `add` does not make, with the reason (conformance/ADD.md).
const NOT_MADE: [(&str, &str); 3] = [
    ("valve", "A Valve is not a type. Make a Predicate and a Filter, and join them with add_valve(predicate, filter)."),
    ("payload", "The runtime makes the Payload. A user does not write one."),
    ("state", "The runtime makes the State. A user does not write one."),
];

/// The role of `kind`, or `None` for a kind that is not one of the five.
pub fn role_of(kind: &str) -> Option<&'static str> {
    ROLES
        .iter()
        .find(|(name, _)| *name == kind)
        .map(|(_, role)| *role)
}

/// The words of a name: each `_` and `-` starts a new one.
fn words_of(name: &str) -> Vec<&str> {
    name.split(['_', '-'])
        .filter(|word| !word.is_empty())
        .collect()
}

/// The first letter of each word becomes a capital: `at_least` gives
/// `AtLeast`, and a name that is PascalCase already does not change.
// cup: allow-plain a naming rule shared by the steps: it joins text, and is not a step
fn pascal(words: &[&str]) -> String {
    let mut name = String::new();
    for word in words {
        let (first, rest) = word.split_at(1);
        name.extend(first.chars().flat_map(char::to_uppercase));
        name.push_str(rest);
    }
    name
}

/// The name of the type in the file name of the linters (CUP-I006): a word
/// starts before a capital that follows a small letter or a digit, and before
/// a capital that is followed by a small letter and follows a capital.
/// `HTTPGetFilter` gives `http_get_filter`.
// cup: allow-plain a naming rule shared by the steps: it is text, not a step of the pipeline
pub fn snake_case(name: &str) -> String {
    let chars: Vec<char> = name.chars().collect();
    let mut snake = String::new();
    for (index, c) in chars.iter().enumerate() {
        let before = index.checked_sub(1).map(|at| chars[at]);
        let after = chars.get(index + 1);
        let starts_word = c.is_uppercase()
            && before.is_some_and(|before| {
                before.is_lowercase()
                    || before.is_ascii_digit()
                    || (before.is_uppercase() && after.is_some_and(|after| after.is_lowercase()))
            });
        if starts_word {
            snake.push('_');
        }
        snake.extend(c.to_lowercase());
    }
    snake
}

/// The type name and the file name, from the kind and the name.
///
/// Reads `kind` and `name`. Writes `type_name` (`DiscountFilter`) and `snake`
/// (`discount_filter`). A kind that `add` does not make, and a name that
/// cannot be used, are refused with exit code 2.
pub struct TypeNameFilter;

impl Filter<AddRun> for TypeNameFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let kind = run.kind.as_str();
        if let Some((_, reason)) = NOT_MADE.iter().find(|(name, _)| *name == kind) {
            return Err(Refusal::usage(*reason).into());
        }
        let Some(role) = role_of(kind) else {
            return Err(Refusal::usage(format!(
                "Unknown kind `{kind}`. The kinds that `add` makes are: filter, predicate, tap, hook, pipeline."
            ))
            .into());
        };
        let name = run.name.as_str();
        let usable = !name.is_empty()
            && name.starts_with(|c: char| c.is_ascii_alphabetic())
            && name
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
        if !usable {
            return Err(Refusal::usage(format!(
                "The name `{name}` cannot be used. A name starts with a letter, and has only letters, digits, _ and -."
            ))
            .into());
        }
        let mut type_name = pascal(&words_of(name));
        if !type_name.ends_with(role) {
            type_name.push_str(role);
        }
        run.snake = snake_case(&type_name);
        run.type_name = type_name;
        Ok(())
    }
}

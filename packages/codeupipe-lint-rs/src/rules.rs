use proc_macro2::Span;

use crate::finding::Finding;
use crate::source::{position, Source};

pub const PARSE_ERROR: &str = "CUP-I000";
pub const LOCAL_TYPE_STEP: &str = "CUP-A003";
pub const UNNAMED_PIPELINE: &str = "CUP-A005";
pub const STATE_READ: &str = "CUP-I003";
pub const ONE_PRIMITIVE_PER_FILE: &str = "CUP-I005";
pub const PRIMITIVE_FILE_NAME: &str = "CUP-I006";
pub const PRIMITIVE_ROLE_SUFFIX: &str = "CUP-I007";
pub const LOGIC_OUTSIDE_PRIMITIVE: &str = "CUP-I008";
pub const MARKER_ALLOWS_NOTHING: &str = "CUP-I009";

/// One rule: its id, its short name, what to do about a finding, and
/// whether a finding is a warning.
pub struct Rule {
    pub id: &'static str,
    pub slug: &'static str,
    pub fix: &'static str,
    pub warning: bool,
}

const NAMED_TYPE: &str = "Declare it at module level as a named type (a Valve predicate: a type that implements Predicate) \
so it can be tested on its own.";

/// The rules, in the order of their ids. The ids and names are those of the
/// Python and TypeScript linters. A rule that the Rust compiler checks
/// (CUP-A001, A002, A008, A009, I004) is not here.
pub const RULES: &[Rule] = &[
    Rule {
        id: LOCAL_TYPE_STEP,
        slug: "local-type-step",
        fix: NAMED_TYPE,
        warning: false,
    },
    Rule {
        id: UNNAMED_PIPELINE,
        slug: "unnamed-pipeline-step",
        fix: "A nested pipeline must be a named pipeline (a type that implements NamedPipeline, nested as \
Pipeline::named(UserOnboarding)), named like a filter. A plain Pipeline can only run at the top level.",
        warning: false,
    },
    Rule {
        id: PARSE_ERROR,
        slug: "parse-error",
        fix: "Fix the syntax error so the file can be checked.",
        warning: false,
    },
    Rule {
        id: STATE_READ,
        slug: "state-read-in-step",
        fix: "A Filter's result and a Valve's decision must depend only on the Payload. Put what the step needs \
into the Payload, or observe State from a Tap or a Hook.",
        warning: false,
    },
    Rule {
        id: ONE_PRIMITIVE_PER_FILE,
        slug: "one-primitive-per-file",
        fix: "Give each Filter, Predicate, Tap, Hook and named Pipeline its own file, so it can be tested alone \
and used again. The pipeline file is where they come together.",
        warning: false,
    },
    Rule {
        id: PRIMITIVE_FILE_NAME,
        slug: "primitive-file-name",
        fix: "The file name of a primitive is its type name in snake_case, so one name gives the other.",
        warning: false,
    },
    Rule {
        id: PRIMITIVE_ROLE_SUFFIX,
        slug: "primitive-role-suffix",
        fix: "A primitive's type name ends with its role (Filter, Tap, Hook, Predicate, Pipeline), so the name \
tells what the type is.",
        warning: false,
    },
    Rule {
        id: LOGIC_OUTSIDE_PRIMITIVE,
        slug: "logic-outside-primitive",
        fix: "Write it as a primitive, so that the pipeline has the logic and it can be tested as a step. For \
logic that must be plain code, say why: // cup: allow-plain <reason>",
        warning: true,
    },
    Rule {
        id: MARKER_ALLOWS_NOTHING,
        slug: "marker-allows-nothing",
        fix: "Remove it, or put it on the line of the finding that it is for. A comment that allows nothing says \
that the code has an exception that it does not have.",
        warning: true,
    },
];

/// The rule with the id `id`.
pub fn rule(id: &str) -> Option<&'static Rule> {
    RULES.iter().find(|rule| rule.id == id)
}

/// A Finding of `rule` at `at`. Its message reads `<what>. <fix>`.
pub fn make_finding(
    source: &Source,
    at: Span,
    id: &str,
    what: &str,
    call_line: Option<usize>,
) -> Finding {
    let (line, col) = position(at);
    let rule = rule(id).expect("a rule of this linter");
    Finding {
        path: source.path.clone(),
        line,
        col,
        rule: id.to_string(),
        slug: rule.slug.to_string(),
        message: format!("{what}. {}", rule.fix),
        call_line: call_line.filter(|call_line| *call_line != line),
        warning: rule.warning,
    }
}

use std::collections::{HashMap, HashSet};

use codeupipe::{Filter, StepError};
use syn::spanned::Spanned;
use syn::visit::{self, Visit};
use syn::{Expr, GenericArgument, Member, PathArguments, Type};

use crate::finding::Finding;
use crate::lint_run::LintRun;
use crate::primitive_kind::{self_type_name, PrimitiveKind};
use crate::rules::{make_finding, STATE_READ};
use crate::source::{position, text_of, Source};

/// The methods of State that read it.
const STATE_MEMBERS: &[&str] = &["executed", "skipped", "errors", "timings"];

/// Types that hold a value of the type in them: a field of `Rc<State>` holds a State.
const HOLDERS: &[&str] = &[
    "Rc", "Arc", "RefCell", "Cell", "Mutex", "RwLock", "Box", "Option", "Weak",
];

/// CUP-I003: a Filter (`call`) or a Predicate (`test`) that reads the State
/// of a pipeline.
///
/// Flagged: `<x>.state()` followed by a method of State (`executed`,
/// `skipped`, `errors`, `timings`); `<pipeline>.state()` when the name says
/// it is a pipeline (`self.pipeline.borrow().state()`); and a field of the
/// step that holds a State (`seen: Rc<State>`). Not flagged: `self.state()`
/// (the step's own method), a State that the step makes, a Payload key named
/// "state", and anything in a Tap or a Hook.
///
/// Reads `sources`. Writes `findings`.
pub struct AnalyzeStateReadsFilter;

impl Filter<LintRun> for AnalyzeStateReadsFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        for source in &run.sources {
            let mut fields = StateFields::default();
            fields.visit_file(&source.tree);
            let mut steps = StepBodies {
                source,
                fields: &fields.by_type,
                findings: Vec::new(),
            };
            steps.visit_file(&source.tree);
            run.findings.append(&mut steps.findings);
        }
        Ok(())
    }
}

/// The fields of each struct of a file that hold a State.
#[derive(Default)]
struct StateFields {
    by_type: HashMap<String, HashSet<String>>,
}

impl<'ast> Visit<'ast> for StateFields {
    fn visit_item_struct(&mut self, item: &'ast syn::ItemStruct) {
        let held: HashSet<String> = item
            .fields
            .iter()
            .filter(|field| holds_state(&field.ty))
            .filter_map(|field| field.ident.as_ref().map(ToString::to_string))
            .collect();
        self.by_type.insert(item.ident.to_string(), held);
        visit::visit_item_struct(self, item);
    }
}

// cup: allow-plain used by the analysis Filter: it reads a type of the syntax tree
fn holds_state(ty: &Type) -> bool {
    match ty {
        Type::Reference(reference) => holds_state(&reference.elem),
        Type::Path(path) => path.path.segments.last().is_some_and(|last| {
            let held = || {
                match &last.arguments {
                PathArguments::AngleBracketed(arguments) => arguments.args.iter().any(|argument| {
                    matches!(argument, GenericArgument::Type(inner) if holds_state(inner))
                }),
                _ => false,
            }
            };
            last.ident == "State" || (HOLDERS.iter().any(|holder| last.ident == holder) && held())
        }),
        _ => false,
    }
}

/// Finds the State reads in each `call` of a Filter and `test` of a Predicate.
struct StepBodies<'a> {
    source: &'a Source,
    fields: &'a HashMap<String, HashSet<String>>,
    findings: Vec<Finding>,
}

// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
impl<'ast> Visit<'ast> for StepBodies<'_> {
    fn visit_item_impl(&mut self, item: &'ast syn::ItemImpl) {
        let kind = item
            .trait_
            .as_ref()
            .and_then(|(_, path, _)| PrimitiveKind::of_trait(path));
        let method = match kind {
            Some(PrimitiveKind::Filter) => "call",
            Some(PrimitiveKind::Predicate) => "test",
            _ => return visit::visit_item_impl(self, item),
        };
        let none = HashSet::new();
        let fields = self_type_name(&item.self_ty)
            .and_then(|name| self.fields.get(&name))
            .unwrap_or(&none);
        let mut reads = Reads {
            source: self.source,
            fields,
            found: Vec::new(),
        };
        for inner in &item.items {
            if let syn::ImplItem::Fn(function) = inner {
                if function.sig.ident == method {
                    reads.visit_block(&function.block);
                }
            }
        }
        self.findings.append(&mut reads.found);
    }
}

/// The State reads in the body of one step.
struct Reads<'a> {
    source: &'a Source,
    fields: &'a HashSet<String>,
    found: Vec<Finding>,
}

// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
impl Reads<'_> {
    fn flag(&mut self, read: &dyn Spanned) {
        let span = read.span();
        let at = position(span);
        if self
            .found
            .iter()
            .any(|finding| (finding.line, finding.col) == at)
        {
            return;
        }
        let what = format!(
            "Step reads pipeline State (`{}`)",
            text_of(&self.source.text, span)
        );
        self.found
            .push(make_finding(self.source, span, STATE_READ, &what, None));
    }
}

// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
impl<'ast> Visit<'ast> for Reads<'_> {
    fn visit_item(&mut self, _: &'ast syn::Item) {
        // An item in the body has its own scope.
    }

    fn visit_expr_method_call(&mut self, call: &'ast syn::ExprMethodCall) {
        if STATE_MEMBERS.iter().any(|member| call.method == member) && is_state_call(&call.receiver)
        {
            self.flag(&call.receiver);
        } else if is_state_call_on(call) && names_a_pipeline(&call.receiver) {
            self.flag(call);
        }
        visit::visit_expr_method_call(self, call);
    }

    fn visit_expr_field(&mut self, field: &'ast syn::ExprField) {
        let held = match &field.member {
            Member::Named(name) => is_self(&field.base) && self.fields.contains(&name.to_string()),
            Member::Unnamed(_) => false,
        };
        if held {
            self.flag(field);
        }
        visit::visit_expr_field(self, field);
    }
}

/// `<x>.state()`, where `<x>` is not `self`.
fn is_state_call(value: &Expr) -> bool {
    matches!(value, Expr::MethodCall(call) if is_state_call_on(call))
}

fn is_state_call_on(call: &syn::ExprMethodCall) -> bool {
    call.method == "state" && call.args.is_empty() && !is_self(&call.receiver)
}

fn is_self(value: &Expr) -> bool {
    matches!(value, Expr::Path(path) if path.path.is_ident("self"))
}

/// The name of `value`, past the method calls on it, says it is a pipeline:
/// `self.pipeline.borrow().upgrade()`, `inner_pipeline`.
// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
fn names_a_pipeline(value: &Expr) -> bool {
    let name = match value {
        Expr::MethodCall(call) => return names_a_pipeline(&call.receiver),
        Expr::Paren(inner) => return names_a_pipeline(&inner.expr),
        Expr::Reference(inner) => return names_a_pipeline(&inner.expr),
        Expr::Unary(inner) => return names_a_pipeline(&inner.expr),
        Expr::Field(field) => match &field.member {
            Member::Named(name) => name.to_string(),
            Member::Unnamed(_) => return false,
        },
        Expr::Path(path) => path
            .path
            .segments
            .last()
            .map(|s| s.ident.to_string())
            .unwrap_or_default(),
        _ => return false,
    };
    name.to_lowercase().contains("pipeline")
}

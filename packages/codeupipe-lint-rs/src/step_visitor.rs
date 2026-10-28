//! Finds the steps that CUP-A003 and CUP-A005 are about, with the names in
//! scope at each `add_...` call.

use syn::spanned::Spanned;
use syn::visit::{self, Visit};
use syn::{Expr, Item, Pat, Stmt};

use crate::finding::Finding;
use crate::rules::{make_finding, LOCAL_TYPE_STEP, UNNAMED_PIPELINE};
use crate::source::{position, text_of, Source};

/// How far a name is followed, from a binding to the value it was given.
const FOLLOW: usize = 8;

/// A block, a function or a closure: the names that it declares.
#[derive(Default)]
struct Scope {
    /// The types declared in a block. A block's items are seen in all of it.
    types: Vec<String>,
    /// The bindings, in order: a `let` with its value, or a parameter or a
    /// pattern with none.
    bindings: Vec<(String, Option<Expr>)>,
    /// A function: it does not see the bindings of the code around it.
    function: bool,
}

/// What is wrong with a step: the rule, and words that say what the value is.
struct Verdict {
    rule: &'static str,
    what: String,
}

/// Visits a file and finds the steps of CUP-A003 and CUP-A005.
pub struct StepVisitor<'a> {
    source: &'a Source,
    scopes: Vec<Scope>,
    pub findings: Vec<Finding>,
}

// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
impl<'a> StepVisitor<'a> {
    pub fn new(source: &'a Source) -> Self {
        StepVisitor {
            source,
            scopes: Vec::new(),
            findings: Vec::new(),
        }
    }

    fn in_scope(&mut self, function: bool, types: Vec<String>, walk: impl FnOnce(&mut Self)) {
        self.scopes.push(Scope {
            types,
            function,
            bindings: Vec::new(),
        });
        walk(self);
        self.scopes.pop();
    }

    fn bind(&mut self, name: String, value: Option<Expr>) {
        if let Some(scope) = self.scopes.last_mut() {
            scope.bindings.push((name, value));
        }
    }

    /// The value that the binding `name` was given: `None` when the name is
    /// not bound, `Some(None)` when it is bound with no value to follow.
    fn binding(&self, name: &str) -> Option<Option<&Expr>> {
        for scope in self.scopes.iter().rev() {
            if let Some((_, value)) = scope.bindings.iter().rev().find(|(bound, _)| bound == name) {
                return Some(value.as_ref());
            }
            if scope.function {
                return None;
            }
        }
        None
    }

    /// The type `name` is declared in a block of a function.
    fn is_local_type(&self, name: &str) -> bool {
        self.scopes
            .iter()
            .any(|scope| scope.types.iter().any(|declared| declared == name))
    }

    fn check_call(&mut self, call: &syn::ExprMethodCall) {
        let roles: &[&str] = match call.method.to_string().as_str() {
            "add_filter" => &["Filter"],
            "add_tap" => &["Tap"],
            "add_pipeline" => &["Pipeline"],
            "add_valve" => &["Valve predicate", "Valve filter"],
            _ => &[],
        };
        let call_line = position(call.method.span()).0;
        for (role, argument) in roles.iter().zip(&call.args) {
            if let Some(verdict) = self.classify(argument, role, 0) {
                let what = format!("{role} {}", verdict.what);
                let finding = make_finding(
                    self.source,
                    argument.span(),
                    verdict.rule,
                    &what,
                    Some(call_line),
                );
                self.findings.push(finding);
            }
        }
    }

    /// What is wrong with `value` as a step of `role`, if anything.
    fn classify(&self, value: &Expr, role: &str, depth: usize) -> Option<Verdict> {
        if depth > FOLLOW {
            return None;
        }
        match unwrap(value) {
            Expr::Path(path) if path.qself.is_none() && path.path.segments.len() == 1 => {
                let name = path.path.segments[0].ident.to_string();
                match self.binding(&name) {
                    Some(Some(bound)) => {
                        self.classify(bound, role, depth + 1)
                            .map(|verdict| Verdict {
                                rule: verdict.rule,
                                what: format!("`{name}` {}", verdict.what),
                            })
                    }
                    Some(None) => None,
                    None => self.local_type(&name),
                }
            }
            Expr::Struct(value) => self.type_of_path(&value.path),
            Expr::Call(call) => {
                let Expr::Path(function) = &*call.func else {
                    return None;
                };
                let names: Vec<String> = function
                    .path
                    .segments
                    .iter()
                    .map(|s| s.ident.to_string())
                    .collect();
                let names: Vec<&str> = names.iter().map(String::as_str).collect();
                match names.as_slice() {
                    [.., "Pipeline", "new" | "default"] if role == "Pipeline" => Some(Verdict {
                        rule: UNNAMED_PIPELINE,
                        what: format!("is a plain `{}`", text_of(&self.source.text, call.span())),
                    }),
                    [.., "Pipeline", "named"] => call
                        .args
                        .first()
                        .and_then(|named| self.classify(named, "named", depth + 1)),
                    // `LocalTap::new()`, and `LocalTap(1)` for a tuple struct.
                    [name, _] | [name] => self.local_type(name),
                    _ => None,
                }
            }
            Expr::MethodCall(call) if call.method == "clone" && call.args.is_empty() => {
                self.classify(&call.receiver, role, depth + 1)
            }
            _ => None,
        }
    }

    fn type_of_path(&self, path: &syn::Path) -> Option<Verdict> {
        match path.segments.len() {
            1 => self.local_type(&path.segments[0].ident.to_string()),
            _ => None,
        }
    }

    fn local_type(&self, name: &str) -> Option<Verdict> {
        self.is_local_type(name).then(|| Verdict {
            rule: LOCAL_TYPE_STEP,
            what: format!("is an instance of `{name}`, a type that is declared in a function"),
        })
    }
}

/// `value` without the parentheses and the `&` around it.
// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
fn unwrap(value: &Expr) -> &Expr {
    match value {
        Expr::Paren(inner) => unwrap(&inner.expr),
        Expr::Group(inner) => unwrap(&inner.expr),
        Expr::Reference(inner) => unwrap(&inner.expr),
        _ => value,
    }
}

/// The name of a pattern that binds one name: `x`, `mut x`, `x: T`.
// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
fn name_of(pattern: &Pat) -> Option<String> {
    match pattern {
        Pat::Ident(ident) if ident.subpat.is_none() => Some(ident.ident.to_string()),
        Pat::Type(typed) => name_of(&typed.pat),
        _ => None,
    }
}

// cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read source code
impl<'ast> Visit<'ast> for StepVisitor<'_> {
    fn visit_block(&mut self, block: &'ast syn::Block) {
        let types = block
            .stmts
            .iter()
            .filter_map(|stmt| match stmt {
                Stmt::Item(Item::Struct(item)) => Some(item.ident.to_string()),
                Stmt::Item(Item::Enum(item)) => Some(item.ident.to_string()),
                Stmt::Item(Item::Union(item)) => Some(item.ident.to_string()),
                _ => None,
            })
            .collect();
        self.in_scope(false, types, |me| visit::visit_block(me, block));
    }

    fn visit_item_fn(&mut self, item: &'ast syn::ItemFn) {
        self.in_scope(true, Vec::new(), |me| visit::visit_item_fn(me, item));
    }

    fn visit_impl_item_fn(&mut self, item: &'ast syn::ImplItemFn) {
        self.in_scope(true, Vec::new(), |me| visit::visit_impl_item_fn(me, item));
    }

    fn visit_trait_item_fn(&mut self, item: &'ast syn::TraitItemFn) {
        self.in_scope(true, Vec::new(), |me| visit::visit_trait_item_fn(me, item));
    }

    fn visit_expr_closure(&mut self, closure: &'ast syn::ExprClosure) {
        self.in_scope(false, Vec::new(), |me| {
            visit::visit_expr_closure(me, closure)
        });
    }

    fn visit_arm(&mut self, arm: &'ast syn::Arm) {
        self.in_scope(false, Vec::new(), |me| visit::visit_arm(me, arm));
    }

    fn visit_expr_for_loop(&mut self, for_loop: &'ast syn::ExprForLoop) {
        self.in_scope(false, Vec::new(), |me| {
            visit::visit_expr_for_loop(me, for_loop)
        });
    }

    fn visit_local(&mut self, local: &'ast syn::Local) {
        if let Some(init) = &local.init {
            self.visit_expr(&init.expr);
            if let Some((_, diverge)) = &init.diverge {
                self.visit_expr(diverge);
            }
        }
        match name_of(&local.pat) {
            Some(name) => self.bind(name, local.init.as_ref().map(|init| (*init.expr).clone())),
            None => self.visit_pat(&local.pat),
        }
    }

    fn visit_pat_ident(&mut self, pattern: &'ast syn::PatIdent) {
        self.bind(pattern.ident.to_string(), None);
        visit::visit_pat_ident(self, pattern);
    }

    fn visit_expr_method_call(&mut self, call: &'ast syn::ExprMethodCall) {
        self.check_call(call);
        visit::visit_expr_method_call(self, call);
    }
}

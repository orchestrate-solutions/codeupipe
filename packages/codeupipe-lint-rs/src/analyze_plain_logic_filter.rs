use codeupipe::{Filter, StepError};
use proc_macro2::Span;
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::Item;

use crate::lint_run::LintRun;
use crate::logic::has_logic;
use crate::primitive_kind::{
    attributes_of, is_test_file, is_test_only, primitive_names, self_type_name,
};
use crate::rules::{make_finding, LOGIC_OUTSIDE_PRIMITIVE};
use crate::source::Source;

const WHAT: &str = "has logic and is not a Filter, a Predicate, a Tap, a Hook or a Pipeline";

/// CUP-I008, a warning: logic that is not in a primitive.
///
/// A project that uses codeupipe writes its logic as Filters, Predicates,
/// Taps, Hooks and Pipelines. Logic in a plain function or a plain type works
/// as well, so nothing else shows the mistake. This rule shows it.
///
/// Logic is a decision or a loop: `if`, `match`, `for`, `while`, `loop`,
/// `let ... else`. Flagged: a function, an `impl` of a type that is not a
/// primitive (once for each `impl`), a trait with a default method, and the
/// first `const` or `static` whose value has logic. Modules of the file are
/// checked the same way. Not flagged: the code of a primitive (each `impl`
/// of a type that implements a primitive trait), code with no logic, code
/// for the tests only (`#[test]`, `#[cfg(test)]`), and the files of `tests/`.
///
/// Reads `sources`. Writes `findings`.
pub struct AnalyzePlainLogicFilter;

impl Filter<LintRun> for AnalyzePlainLogicFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        for source in run
            .sources
            .iter()
            .filter(|source| !is_test_file(&source.path))
        {
            let mut primitives = Vec::new();
            primitive_names(&source.tree.items, &mut primitives);
            let mut module_code = None;
            let mut found = Vec::new();
            Self::in_items(
                &source.tree.items,
                &primitives,
                &mut found,
                &mut module_code,
            );
            found
                .extend(module_code.map(|at| (at, "The code at the top of this file".to_string())));
            for (at, what) in found {
                run.findings.push(Self::finding(source, at, &what));
            }
        }
        Ok(())
    }
}

impl AnalyzePlainLogicFilter {
    fn finding(source: &Source, at: Span, what: &str) -> crate::finding::Finding {
        make_finding(
            source,
            at,
            LOGIC_OUTSIDE_PRIMITIVE,
            &format!("{what} {WHAT}"),
            None,
        )
    }

    /// The items of a file or a module with logic that is not in a primitive.
    fn in_items(
        items: &[Item],
        primitives: &[String],
        found: &mut Vec<(Span, String)>,
        module_code: &mut Option<Span>,
    ) {
        for item in items
            .iter()
            .filter(|item| !is_test_only(attributes_of(item)))
        {
            match item {
                Item::Fn(function) => {
                    if has_logic(|v| v.visit_block(&function.block)) {
                        found.push((
                            function.sig.ident.span(),
                            format!("Function `{}`", function.sig.ident),
                        ));
                    }
                }
                Item::Impl(block) => {
                    let name = self_type_name(&block.self_ty).unwrap_or_default();
                    if !primitives.contains(&name) && has_logic(|v| v.visit_item_impl(block)) {
                        found.push((block.impl_token.span(), format!("Type `{name}`")));
                    }
                }
                Item::Trait(definition) => {
                    if has_logic(|v| v.visit_item_trait(definition)) {
                        found.push((
                            definition.ident.span(),
                            format!("Trait `{}`", definition.ident),
                        ));
                    }
                }
                Item::Const(constant) => {
                    if module_code.is_none() && has_logic(|v| v.visit_expr(&constant.expr)) {
                        *module_code = Some(constant.span());
                    }
                }
                Item::Static(value) => {
                    if module_code.is_none() && has_logic(|v| v.visit_expr(&value.expr)) {
                        *module_code = Some(value.span());
                    }
                }
                Item::Mod(module) => {
                    if let Some((_, inner)) = &module.content {
                        Self::in_items(inner, primitives, found, module_code);
                    }
                }
                _ => {}
            }
        }
    }
}

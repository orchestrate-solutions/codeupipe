use codeupipe::{Filter, StepError};
use quote::{format_ident, ToTokens};
use syn::spanned::Spanned;
use syn::visit_mut::VisitMut;
use syn::{FnArg, ImplItem, ImplItemFn, Item, Pat, Type, UseTree};

use crate::compile_run::CompileRun;
use crate::lowered_step::LoweredStep;
use crate::payload_rewriter::PayloadRewriter;
use crate::refusal::Refusal;
use crate::source::Source;
use crate::step::{Role, Step, StepPlan};

/// Each step to a plain function on the compiled struct: the body of its
/// `call` (a Filter), `test` (a Predicate) or `observe` (a Tap), rewritten by
/// PayloadRewriter. The `use` items of the step file come with it.
pub struct LowerStepsFilter;

impl LowerStepsFilter {
    fn snake(name: &str) -> String {
        let mut out = String::new();
        for (at, c) in name.chars().enumerate() {
            if c.is_uppercase() && at > 0 {
                out.push('_');
            }
            out.extend(c.to_lowercase());
        }
        out
    }

    fn type_name(ty: &Type) -> String {
        match ty {
            Type::Path(path) => path
                .path
                .segments
                .last()
                .map(|s| s.ident.to_string())
                .unwrap_or_default(),
            _ => String::new(),
        }
    }

    /// A `use` that the compiled module keeps: not of codeupipe, and not of the project (`super`, `crate`, `self`).
    fn kept_use(tree: &UseTree) -> bool {
        match tree {
            UseTree::Path(path) => {
                !["codeupipe", "super", "crate", "self"].contains(&path.ident.to_string().as_str())
            }
            UseTree::Name(name) => name.ident != "codeupipe",
            _ => true,
        }
    }

    /// The method of the role in `impl <Trait> for <step>`, with its file.
    fn method<'a>(sources: &'a [Source], step: &Step) -> Option<(&'a Source, &'a ImplItemFn)> {
        let (trait_name, method) = match step.role {
            Role::Filter => ("Filter", "call"),
            Role::Predicate => ("Predicate", "test"),
            Role::Tap => ("Tap", "observe"),
        };
        sources.iter().find_map(|source| {
            source.tree.items.iter().find_map(|item| match item {
                Item::Impl(imp)
                    if Self::type_name(&imp.self_ty) == step.type_name
                        && imp.trait_.as_ref().is_some_and(|(_, path, _)| {
                            path.segments.last().is_some_and(|s| s.ident == trait_name)
                        }) =>
                {
                    imp.items.iter().find_map(|item| match item {
                        ImplItem::Fn(func) if func.sig.ident == method => Some((source, func)),
                        _ => None,
                    })
                }
                _ => None,
            })
        })
    }

    fn lower(run: &mut CompileRun, step: &Step, name: String) -> Result<(), Refusal> {
        let sources = run.sources.clone();
        let Some((source, method)) = Self::method(&sources, step) else {
            let role = format!("{:?}", step.role);
            return Err(Refusal::new(
                step.place.clone(),
                format!(
                    "There is no `impl {role} for {}` in the paths",
                    step.type_name
                ),
                "Give the file of each step",
            ));
        };
        let payload = method.sig.inputs.iter().find_map(|input| match input {
            FnArg::Typed(typed) => match &*typed.pat {
                Pat::Ident(ident) => Some(ident.ident.to_string()),
                _ => None,
            },
            FnArg::Receiver(_) => None,
        });
        let Some(payload) = payload else {
            return Err(Refusal::new(
                crate::place::Place::of(&source.path, method.sig.span()),
                "The Payload parameter has no name",
                "Give it a name",
            ));
        };
        let mut rewriter = PayloadRewriter {
            path: &source.path,
            step: &step.type_name,
            payload: payload.clone(),
            settings: &step.settings,
            writes: step.role == Role::Filter,
            uses: Vec::new(),
            refusal: None,
        };
        let mut block = method.block.clone();
        rewriter.visit_block_mut(&mut block);
        rewriter.check_left(block.to_token_stream());
        if let Some(refusal) = rewriter.refusal {
            return Err(refusal);
        }
        run.uses.extend(rewriter.uses);
        let data = format_ident!("{}", run.data);
        let payload = format_ident!("{}", payload);
        let function = format_ident!("{}", name);
        let doc = format!(" {}", step.type_name);
        let item: syn::ItemFn = match step.role {
            Role::Filter => {
                syn::parse_quote!(#[doc = #doc] fn #function(#payload: &mut #data) -> Result<(), StepError> #block)
            }
            Role::Predicate => {
                syn::parse_quote!(#[doc = #doc] fn #function(#payload: &#data) -> bool #block)
            }
            Role::Tap => {
                syn::parse_quote!(#[doc = #doc] fn #function(#payload: &#data) -> Result<(), StepError> #block)
            }
        };
        for item in &source.tree.items {
            if let Item::Use(import) = item {
                if Self::kept_use(&import.tree)
                    && !run.imports.iter().any(|kept| {
                        kept.to_token_stream().to_string() == import.to_token_stream().to_string()
                    })
                {
                    run.imports.push(import.clone());
                }
            }
        }
        run.functions.push(LoweredStep {
            role: step.role,
            name,
            type_name: step.type_name.clone(),
            item,
        });
        Ok(())
    }
}

impl Filter<CompileRun> for LowerStepsFilter {
    fn call(&self, run: &mut CompileRun) -> Result<(), StepError> {
        for (at, plan) in run.steps.clone().iter().enumerate() {
            let number = format!("cup_{:02}", at + 1);
            match plan {
                StepPlan::Filter(step) | StepPlan::Tap(step) => Self::lower(
                    run,
                    step,
                    format!("{number}_{}", Self::snake(&step.type_name)),
                )?,
                StepPlan::Valve(predicate, filter) => {
                    Self::lower(
                        run,
                        predicate,
                        format!("{number}_when_{}", Self::snake(&predicate.type_name)),
                    )?;
                    Self::lower(
                        run,
                        filter,
                        format!("{number}_{}", Self::snake(&filter.type_name)),
                    )?;
                }
            }
        }
        Ok(())
    }
}

use codeupipe::{Filter, StepError};
use quote::{format_ident, quote};

use crate::compile_run::CompileRun;
use crate::step::{Role, StepPlan};

/// The compiled module: the struct of the keys, the function of each step,
/// and `run`, formatted as Rust.
pub struct EmitModuleFilter;

impl Filter<CompileRun> for EmitModuleFilter {
    fn call(&self, run: &mut CompileRun) -> Result<(), StepError> {
        let data = format_ident!("{}", run.data);
        let pipeline = &run.pipeline;
        let head = [
            format!(
                " Written by codeupipe-compile from {pipeline}. Do not edit it: compile again."
            ),
            String::new(),
            " Plain Rust, with no codeupipe: a struct with one field for each key that".to_string(),
            " the steps use, and one function for each step. It has no State and no".to_string(),
            " Hooks. A Tap failure does not stop the run.".to_string(),
        ];
        let struct_doc =
            format!(" The data of {pipeline}: one field for each key that its steps use.");
        let run_doc = format!(" Runs the steps of {pipeline}, in order, on a copy of `input`.");
        let fields = run.keys.iter().map(|(key, field, key_type)| {
            let field = format_ident!("{}", field);
            let ty = key_type.rust();
            let doc = format!(" The key {key:?}.");
            quote!(#[doc = #doc] pub #field: Option<#ty>,)
        });
        let functions = run.functions.iter().map(|lowered| &lowered.item);
        let mut lowered = run.functions.iter();
        let mut calls = Vec::new();
        for plan in &run.steps {
            let mut next =
                || format_ident!("{}", lowered.next().expect("a function for each step").name);
            calls.push(match plan {
                StepPlan::Filter(_) => {
                    let f = next();
                    quote!(#f(&mut payload)?;)
                }
                StepPlan::Valve(..) => {
                    let (predicate, filter) = (next(), next());
                    quote!(if #predicate(&payload) { #filter(&mut payload)?; })
                }
                StepPlan::Tap(_) => {
                    let t = next();
                    quote!(let _ = #t(&payload);)
                }
            });
        }
        debug_assert!(run
            .functions
            .iter()
            .all(|f| matches!(f.role, Role::Filter | Role::Predicate | Role::Tap)));
        let imports = &run.imports;
        let file = quote! {
            #(#![doc = #head])*
            #(#imports)*
            #[doc = " The error of a step."]
            pub type StepError = Box<dyn std::error::Error + Send + Sync>;
            #[doc = #struct_doc]
            #[derive(Clone, Debug, Default, PartialEq)]
            pub struct #data {
                #(#fields)*
            }
            #(#functions)*
            #[doc = #run_doc]
            pub fn run(input: &#data) -> Result<#data, StepError> {
                let mut payload = input.clone();
                #(#calls)*
                Ok(payload)
            }
        };
        let tree: syn::File = syn::parse2(file)?;
        run.module = prettyplease::unparse(&tree);
        Ok(())
    }
}

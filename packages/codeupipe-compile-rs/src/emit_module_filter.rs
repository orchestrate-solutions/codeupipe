use codeupipe::{Filter, StepError};
use quote::{format_ident, quote};

use crate::compile_run::CompileRun;
use crate::key_type::KeyType;
use crate::step::{Role, StepPlan};

/// The compiled module: the struct of the keys, the struct that the steps
/// work on (when a key is text), the function of each text setting and of
/// each step, and `run`, formatted as Rust.
pub struct EmitModuleFilter;

impl EmitModuleFilter {
    /// The struct that borrows the caller's text, and `run` on it: the text
    /// that no step wrote is copied into the output at the end.
    fn work_and_run(
        run: &CompileRun,
        work: &str,
        calls: &[proc_macro2::TokenStream],
    ) -> proc_macro2::TokenStream {
        let data = format_ident!("{}", run.data);
        let work = format_ident!("{}", work);
        let pipeline = &run.pipeline;
        let work_doc = [
            format!(" The data while the steps of {pipeline} run. Text that no step has"),
            " written yet is the caller's, borrowed and not copied.".to_string(),
        ];
        let run_doc = [
            format!(" Runs the steps of {pipeline}, in order. The caller's text is read where"),
            " it is: only the text that no step wrote is copied into the output.".to_string(),
        ];
        let mut fields = Vec::new();
        let mut from_input = Vec::new();
        let mut to_output = Vec::new();
        for (_, field, key_type) in &run.keys {
            let field = format_ident!("{}", field);
            if *key_type == KeyType::Text {
                fields.push(quote!(#field: Option<::std::borrow::Cow<'a, str>>,));
                from_input.push(
                    quote!(#field: input.#field.as_deref().map(::std::borrow::Cow::Borrowed),),
                );
                to_output.push(quote!(#field: payload.#field.map(::std::borrow::Cow::into_owned),));
            } else {
                let ty = key_type.rust();
                fields.push(quote!(#field: Option<#ty>,));
                from_input.push(quote!(#field: input.#field,));
                to_output.push(quote!(#field: payload.#field,));
            }
        }
        let constants = &run.constants;
        let functions = run.functions.iter().map(|lowered| &lowered.item);
        quote! {
            #(#[doc = #work_doc])*
            struct #work<'a> {
                #(#fields)*
            }
            #(#constants)*
            #(#functions)*
            #(#[doc = #run_doc])*
            pub fn run(input: &#data) -> Result<#data, StepError> {
                let mut payload = #work { #(#from_input)* };
                #(#calls)*
                Ok(#data { #(#to_output)* })
            }
        }
    }
}

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
        let constants = &run.constants;
        let rest = match &run.work {
            Some(work) => Self::work_and_run(run, work, &calls),
            None => quote! {
                #(#constants)*
                #(#functions)*
                #[doc = #run_doc]
                pub fn run(input: &#data) -> Result<#data, StepError> {
                    let mut payload = input.clone();
                    #(#calls)*
                    Ok(payload)
                }
            },
        };
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
            #rest
        };
        let tree: syn::File = syn::parse2(file)?;
        run.module = prettyplease::unparse(&tree);
        Ok(())
    }
}

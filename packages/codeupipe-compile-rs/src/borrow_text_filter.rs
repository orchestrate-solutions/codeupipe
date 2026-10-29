use codeupipe::{Filter, StepError};
use quote::format_ident;
use syn::visit_mut::VisitMut;
use syn::{FnArg, Pat};

use crate::compile_run::CompileRun;
use crate::key_type::KeyType;
use crate::step::Role;
use crate::text_write_rewriter::TextWriteRewriter;

/// When a key is text, the steps work on a struct that borrows the caller's
/// text (`SignupWork`), so that `run` does not copy text that a step writes
/// over. A write of text owns its text. With no text key, the steps work on
/// the struct of the data, which is cheap to copy.
pub struct BorrowTextFilter;

impl Filter<CompileRun> for BorrowTextFilter {
    fn call(&self, run: &mut CompileRun) -> Result<(), StepError> {
        let text: Vec<String> = run
            .keys
            .iter()
            .filter(|(_, _, key_type)| *key_type == KeyType::Text)
            .map(|(_, field, _)| field.clone())
            .collect();
        if text.is_empty() {
            return Ok(());
        }
        let work = format!("{}Work", run.data.strip_suffix("Data").unwrap_or(&run.data));
        let work_type = format_ident!("{}", work);
        for lowered in &mut run.functions {
            let Some(FnArg::Typed(param)) = lowered.item.sig.inputs.first_mut() else {
                continue;
            };
            let Pat::Ident(payload) = &*param.pat else {
                continue;
            };
            let payload = payload.ident.to_string();
            *param.ty = match lowered.role {
                Role::Filter => syn::parse_quote!(&mut #work_type<'_>),
                Role::Predicate | Role::Tap => syn::parse_quote!(&#work_type<'_>),
            };
            if lowered.role == Role::Filter {
                TextWriteRewriter {
                    payload,
                    fields: &text,
                }
                .visit_block_mut(&mut lowered.item.block);
            }
        }
        run.work = Some(work);
        Ok(())
    }
}

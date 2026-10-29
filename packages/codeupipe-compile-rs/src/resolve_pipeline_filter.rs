use codeupipe::{Filter, StepError};
use syn::spanned::Spanned;
use syn::{Expr, Fields, ImplItem, Item, Lit, Member, Stmt, Type, UnOp};

use crate::compile_run::CompileRun;
use crate::place::Place;
use crate::refusal::Refusal;
use crate::source::Source;
use crate::step::{Role, Step, StepPlan};

/// Finds `impl NamedPipeline for <pipeline>`, and reads its `add_steps`: each
/// step, its role, and each setting with the literal that the pipeline
/// gives it (from a struct literal or a constructor such as `new`).
pub struct ResolvePipelineFilter;

impl ResolvePipelineFilter {
    /// The last name of a type: `Filter` for `codeupipe::Filter<Payload>`.
    fn last_name(path: &syn::Path) -> String {
        path.segments
            .last()
            .map(|segment| segment.ident.to_string())
            .unwrap_or_default()
    }

    fn type_name(ty: &Type) -> String {
        match ty {
            Type::Path(path) => Self::last_name(&path.path),
            _ => String::new(),
        }
    }

    /// A literal setting: text, a number (also negative), or true or false.
    fn is_literal(expr: &Expr) -> bool {
        match expr {
            Expr::Lit(_) => true,
            Expr::Unary(unary) => {
                matches!(unary.op, UnOp::Neg(_))
                    && matches!(&*unary.expr, Expr::Lit(lit) if matches!(lit.lit, Lit::Int(_) | Lit::Float(_)))
            }
            Expr::Paren(paren) => Self::is_literal(&paren.expr),
            _ => false,
        }
    }

    fn has_type(sources: &[Source], name: &str) -> bool {
        sources.iter().any(|source| {
            source.tree.items.iter().any(|item| match item {
                Item::Struct(item) => item.ident == name,
                Item::Enum(item) => item.ident == name,
                _ => false,
            })
        })
    }

    /// The fields of `struct name`, with their types, and the file.
    fn fields(sources: &[Source], name: &str) -> Vec<(String, Type)> {
        for source in sources {
            for item in &source.tree.items {
                if let Item::Struct(item) = item {
                    if item.ident == name {
                        if let Fields::Named(named) = &item.fields {
                            return named
                                .named
                                .iter()
                                .filter_map(|field| {
                                    Some((field.ident.as_ref()?.to_string(), field.ty.clone()))
                                })
                                .collect();
                        }
                    }
                }
            }
        }
        Vec::new()
    }

    /// The setting as the step keeps it: a `String` field gets `String::from(literal)`.
    fn kept(literal: Expr, ty: Option<&Type>) -> Expr {
        match ty {
            Some(ty) if Self::type_name(ty) == "String" => {
                syn::parse_quote!(String::from(#literal))
            }
            _ => literal,
        }
    }

    /// `T`, `T { field: literal }`, or `T::new(literal, ...)` to a step.
    fn step(sources: &[Source], path: &str, expr: &Expr, role: Role) -> Result<Step, Refusal> {
        let place = Place::of(path, expr.span());
        let fix = "Make the step as T, as T { field: literal }, or as T::new(literal, ...)";
        let (type_name, settings) = match expr {
            Expr::Path(p) if p.path.segments.len() == 1 => (Self::last_name(&p.path), Vec::new()),
            Expr::Struct(literal) => {
                let name = Self::last_name(&literal.path);
                let types = Self::fields(sources, &name);
                let mut settings = Vec::new();
                for field in &literal.fields {
                    if !Self::is_literal(&field.expr) {
                        return Err(Refusal::new(
                            Place::of(path, field.expr.span()),
                            "A setting that is not a literal",
                            "Give each setting as text, a number, or true or false",
                        ));
                    }
                    let Member::Named(ident) = &field.member else {
                        return Err(Refusal::new(place, "A step of a tuple struct", fix));
                    };
                    let ty = types
                        .iter()
                        .find(|(name, _)| ident == name)
                        .map(|(_, ty)| ty);
                    settings.push((ident.to_string(), Self::kept(field.expr.clone(), ty)));
                }
                (name, settings)
            }
            Expr::Call(call) => {
                let Expr::Path(func) = &*call.func else {
                    return Err(Refusal::new(
                        place,
                        "A step that is made in another way",
                        fix,
                    ));
                };
                if func.path.segments.len() != 2 {
                    return Err(Refusal::new(
                        place,
                        "A step that is made in another way",
                        fix,
                    ));
                }
                let name = func.path.segments[0].ident.to_string();
                let constructor = func.path.segments[1].ident.to_string();
                for arg in &call.args {
                    if !Self::is_literal(arg) {
                        return Err(Refusal::new(
                            Place::of(path, arg.span()),
                            "A setting that is not a literal",
                            "Give each setting as text, a number, or true or false",
                        ));
                    }
                }
                let args: Vec<Expr> = call.args.iter().cloned().collect();
                (
                    name.clone(),
                    Self::constructor(sources, &name, &constructor, &args, &place)?,
                )
            }
            _ => {
                return Err(Refusal::new(
                    place,
                    "A step that is made in another way",
                    fix,
                ))
            }
        };
        if !Self::has_type(sources, &type_name) {
            return Err(Refusal::new(
                place,
                format!("There is no source for `{type_name}` in the paths"),
                "Give the file of each step",
            ));
        }
        Ok(Step {
            role,
            type_name,
            settings,
            place,
        })
    }

    /// The settings that `T::constructor(args)` gives: each field must be a parameter (perhaps made into a
    /// `String`) or a literal.
    fn constructor(
        sources: &[Source],
        name: &str,
        constructor: &str,
        args: &[Expr],
        place: &Place,
    ) -> Result<Vec<(String, Expr)>, Refusal> {
        for source in sources {
            for item in &source.tree.items {
                let Item::Impl(imp) = item else { continue };
                if imp.trait_.is_some() || Self::type_name(&imp.self_ty) != name {
                    continue;
                }
                for impl_item in &imp.items {
                    let ImplItem::Fn(func) = impl_item else {
                        continue;
                    };
                    if func.sig.ident != constructor {
                        continue;
                    }
                    let params: Vec<String> = func
                        .sig
                        .inputs
                        .iter()
                        .filter_map(|input| match input {
                            syn::FnArg::Typed(typed) => match &*typed.pat {
                                syn::Pat::Ident(ident) => Some(ident.ident.to_string()),
                                _ => None,
                            },
                            _ => None,
                        })
                        .collect();
                    let computes = |span| {
                        Refusal::new(
                            Place::of(&source.path, span),
                            format!("`{name}::{constructor}` computes its settings"),
                            "Keep each parameter as it is, and compute in the method of the step",
                        )
                    };
                    let Some(Stmt::Expr(Expr::Struct(made), None)) = func.block.stmts.last() else {
                        return Err(computes(func.block.span()));
                    };
                    if func.block.stmts.len() != 1 {
                        return Err(computes(func.block.span()));
                    }
                    let types = Self::fields(sources, name);
                    let mut settings = Vec::new();
                    for field in &made.fields {
                        let Member::Named(ident) = &field.member else {
                            return Err(computes(field.span()));
                        };
                        let value = Self::parameter(&field.expr)
                            .and_then(|param| params.iter().position(|p| *p == param))
                            .map(|at| args[at].clone());
                        let value = match value {
                            Some(value) => value,
                            None if Self::is_literal(&field.expr) => field.expr.clone(),
                            None => return Err(computes(field.expr.span())),
                        };
                        let ty = types
                            .iter()
                            .find(|(field_name, _)| ident == field_name)
                            .map(|(_, ty)| ty);
                        settings.push((ident.to_string(), Self::kept(value, ty)));
                    }
                    return Ok(settings);
                }
            }
        }
        Err(Refusal::new(
            place.clone(),
            format!("There is no `{name}::{constructor}` in the paths"),
            "Give the file of each step",
        ))
    }

    /// The parameter that a field keeps: `rate`, `key.to_string()`, `key.into()`, `String::from(key)`.
    fn parameter(expr: &Expr) -> Option<String> {
        match expr {
            Expr::Path(path) if path.path.segments.len() == 1 => Some(Self::last_name(&path.path)),
            Expr::MethodCall(call)
                if call.args.is_empty()
                    && ["to_string", "into", "to_owned"]
                        .contains(&call.method.to_string().as_str()) =>
            {
                Self::parameter(&call.receiver)
            }
            Expr::Call(call)
                if call.args.len() == 1
                    && matches!(&*call.func, Expr::Path(p) if p.path.segments.len() == 2 && p.path.segments[0].ident == "String" && p.path.segments[1].ident == "from") =>
            {
                Self::parameter(&call.args[0])
            }
            _ => None,
        }
    }
}

impl Filter<CompileRun> for ResolvePipelineFilter {
    fn call(&self, run: &mut CompileRun) -> Result<(), StepError> {
        let found = run.sources.iter().find_map(|source| {
            source.tree.items.iter().find_map(|item| match item {
                Item::Impl(imp)
                    if Self::type_name(&imp.self_ty) == run.pipeline
                        && imp.trait_.as_ref().is_some_and(|(_, path, _)| {
                            Self::last_name(path) == "NamedPipeline"
                        }) =>
                {
                    Some((source, imp))
                }
                _ => None,
            })
        });
        let Some((source, imp)) = found else {
            let path = run.paths.first().cloned().unwrap_or_default();
            return Err(Refusal::new(
                Place {
                    path,
                    line: 0,
                    col: 0,
                },
                format!(
                    "There is no `impl NamedPipeline for {}` in the paths",
                    run.pipeline
                ),
                "Give the file of the pipeline, and its name",
            )
            .into());
        };
        if let Some((_, path, _)) = &imp.trait_ {
            if let syn::PathArguments::AngleBracketed(args) =
                &path.segments.last().expect("a trait has a name").arguments
            {
                let payload = args.args.iter().all(|arg| matches!(arg, syn::GenericArgument::Type(ty) if Self::type_name(ty) == "Payload"));
                if !payload {
                    return Err(Refusal::new(
                        Place::of(&source.path, path.span()),
                        "A pipeline of a type of your own",
                        "It is plain data already: compile a pipeline of Payload",
                    )
                    .into());
                }
            }
        }
        let name = run
            .pipeline
            .strip_suffix("Pipeline")
            .unwrap_or(&run.pipeline);
        run.data = format!("{}Data", if name.is_empty() { &run.pipeline } else { name });
        let add_steps = imp.items.iter().find_map(|item| match item {
            ImplItem::Fn(func) if func.sig.ident == "add_steps" => Some(func),
            _ => None,
        });
        let Some(add_steps) = add_steps else {
            return Err(Refusal::new(
                Place::of(&source.path, imp.span()),
                "The pipeline has no add_steps",
                "Add its steps in add_steps",
            )
            .into());
        };
        let mut steps = Vec::new();
        for stmt in &add_steps.block.stmts {
            let Stmt::Expr(Expr::MethodCall(call), Some(_)) = stmt else {
                if matches!(stmt, Stmt::Local(_)) {
                    continue; // a name for a setting: the step that uses it is refused, since a setting is a literal
                }
                return Err(Refusal::new(
                    Place::of(&source.path, stmt.span()),
                    "add_steps does more than add steps",
                    "Keep only the add_... calls",
                )
                .into());
            };
            let place = Place::of(&source.path, call.span());
            let args: Vec<&Expr> = call.args.iter().collect();
            let plan = match (call.method.to_string().as_str(), args.as_slice()) {
                ("add_filter", [step]) => {
                    StepPlan::Filter(Self::step(&run.sources, &source.path, step, Role::Filter)?)
                }
                ("add_tap", [step]) => {
                    StepPlan::Tap(Self::step(&run.sources, &source.path, step, Role::Tap)?)
                }
                ("add_valve", [predicate, filter]) => StepPlan::Valve(
                    Self::step(&run.sources, &source.path, predicate, Role::Predicate)?,
                    Self::step(&run.sources, &source.path, filter, Role::Filter)?,
                ),
                ("use_hook", _) | ("observe", _) => {
                    return Err(Refusal::new(
                        place,
                        "A Hook, or observe(): the compiled code has no lifecycle and no State",
                        "Run the pipeline itself, or take the Hook out",
                    )
                    .into())
                }
                ("add_pipeline", _) => {
                    return Err(Refusal::new(
                        place,
                        "A nested pipeline is not compiled yet",
                        "Add its steps to this pipeline",
                    )
                    .into())
                }
                (method, _) => {
                    return Err(Refusal::new(
                        place,
                        format!("`{method}` is not a call that adds a step"),
                        "Keep only the add_... calls",
                    )
                    .into())
                }
            };
            steps.push(plan);
        }
        run.steps = steps;
        Ok(())
    }
}

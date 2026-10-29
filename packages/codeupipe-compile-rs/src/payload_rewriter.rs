use proc_macro2::{TokenStream, TokenTree};
use quote::{format_ident, ToTokens};
use syn::punctuated::Punctuated;
use syn::spanned::Spanned;
use syn::visit_mut::{self, VisitMut};
use syn::{Expr, Lit, Member, Token};

use crate::key_type::KeyType;
use crate::key_use::KeyUse;
use crate::place::Place;
use crate::refusal::Refusal;

const USE_ONLY: &str =
    "Use the Payload only through get(..).and_then(Value::as_...), has, insert and remove";

/// Rewrites the body of a step for the compiled struct: a key of the Payload
/// becomes a field, and `self.setting` becomes the literal that the pipeline
/// gave it. A `String` setting is made once, by a function of its own, and
/// not at each run. Each other use of the Payload, of `self` or of `Value`
/// is refused.
pub struct PayloadRewriter<'a> {
    pub path: &'a str,
    pub step: &'a str,
    /// The name of the compiled function of the step.
    pub function: &'a str,
    /// The name of the Payload parameter of the step.
    pub payload: String,
    pub settings: &'a [(String, Expr)],
    pub writes: bool,
    pub uses: Vec<KeyUse>,
    /// The function of each `String` setting that the step uses.
    pub constants: Vec<syn::ItemFn>,
    /// True while the rewriter reads a key: a setting is then its literal.
    pub in_key: bool,
    pub refusal: Option<Refusal>,
}

// cup: allow-plain the rewrite of a step body: a walk of its syntax tree, called by LowerStepsFilter
impl PayloadRewriter<'_> {
    /// The field of the compiled struct for a key: the key when it is a name in
    /// Rust, or the key with each other character made `_`.
    pub fn field_of(key: &str) -> String {
        let mut field: String = key
            .chars()
            .map(|c| {
                if c.is_ascii_alphanumeric() || c == '_' {
                    c
                } else {
                    '_'
                }
            })
            .collect();
        if field.is_empty()
            || field.starts_with(|c: char| c.is_ascii_digit())
            || syn::parse_str::<syn::Ident>(&field).is_err()
        {
            field = format!("key_{field}");
        }
        field
    }

    /// The type of a value that a step writes, when the code shows it.
    fn written_type(expr: &Expr) -> Option<KeyType> {
        match expr {
            Expr::Lit(lit) => match lit.lit {
                Lit::Float(_) | Lit::Int(_) => Some(KeyType::Number),
                Lit::Bool(_) => Some(KeyType::Bool),
                Lit::Str(_) => Some(KeyType::Text),
                _ => None,
            },
            Expr::Unary(unary) => {
                Self::written_type(&unary.expr).filter(|ty| *ty == KeyType::Number)
            }
            Expr::Paren(paren) => Self::written_type(&paren.expr),
            Expr::Macro(mac) if mac.mac.path.is_ident("format") => Some(KeyType::Text),
            Expr::Call(call) if matches!(&*call.func, Expr::Path(p) if p.path.segments.len() == 2 && p.path.segments[0].ident == "String") => {
                Some(KeyType::Text)
            }
            Expr::MethodCall(call)
                if ["to_string", "to_owned", "to_lowercase", "to_uppercase"]
                    .contains(&call.method.to_string().as_str()) =>
            {
                Some(KeyType::Text)
            }
            _ => None,
        }
    }

    /// The type that `Value::as_f64`, `Value::as_bool` or `Value::as_str` reads, from `.and_then(..)`.
    fn read_type(arg: &Expr) -> Option<KeyType> {
        let name = match arg {
            Expr::Path(path)
                if path.path.segments.len() == 2 && path.path.segments[0].ident == "Value" =>
            {
                path.path.segments[1].ident.to_string()
            }
            Expr::Closure(closure) if closure.inputs.len() == 1 => match &*closure.body {
                Expr::MethodCall(call) if call.args.is_empty() => call.method.to_string(),
                _ => return None,
            },
            _ => return None,
        };
        match name.as_str() {
            "as_f64" => Some(KeyType::Number),
            "as_bool" => Some(KeyType::Bool),
            "as_str" => Some(KeyType::Text),
            _ => None,
        }
    }

    fn is_self(expr: &Expr) -> bool {
        matches!(expr, Expr::Path(path) if path.path.is_ident("self"))
    }

    fn refuse(&mut self, span: proc_macro2::Span, what: impl Into<String>, fix: &str) {
        if self.refusal.is_none() {
            self.refusal = Some(Refusal::new(Place::of(self.path, span), what, fix));
        }
    }

    fn is_payload(&self, expr: &Expr) -> bool {
        matches!(expr, Expr::Path(path) if path.path.is_ident(&self.payload))
    }

    fn record(
        &mut self,
        key: &str,
        key_type: Option<KeyType>,
        untyped_write: bool,
        span: proc_macro2::Span,
    ) {
        self.uses.push(KeyUse {
            key: key.to_string(),
            key_type,
            untyped_write,
            step: self.step.to_string(),
            place: Place::of(self.path, span),
        });
    }

    /// The value of a setting in the function: its literal, or for a `String` setting
    /// (`String::from(literal)`), the `String` that a function of its own makes once.
    fn setting(&mut self, name: &str, value: &Expr) -> Expr {
        let is_text = matches!(value, Expr::Call(call) if matches!(&*call.func, Expr::Path(p) if p.path.segments.len() == 2 && p.path.segments[0].ident == "String"));
        if self.in_key || !is_text {
            return value.clone();
        }
        let function = format_ident!("{}_{}", self.function, name);
        if !self.constants.iter().any(|made| made.sig.ident == function) {
            let doc = format!(
                " The setting `{name}` of {}, made once and not at each run.",
                self.step
            );
            self.constants.push(syn::parse_quote! {
                #[doc = #doc]
                fn #function() -> &'static String {
                    static VALUE: ::std::sync::OnceLock<String> = ::std::sync::OnceLock::new();
                    VALUE.get_or_init(|| #value)
                }
            });
        }
        // A place of type String, as `self.text` is: each use of it is the same.
        syn::parse_quote!((*#function()))
    }

    /// The text of a key: a literal, perhaps behind `&`, `.to_string()`, `String::from(..)`. Settings are put in first.
    fn key_of(&mut self, arg: &Expr) -> Option<String> {
        let mut arg = arg.clone();
        let in_key = std::mem::replace(&mut self.in_key, true);
        self.visit_expr_mut(&mut arg);
        self.in_key = in_key;
        let mut at = &arg;
        loop {
            match at {
                Expr::Lit(lit) => {
                    if let Lit::Str(text) = &lit.lit {
                        return Some(text.value());
                    }
                    break;
                }
                Expr::Reference(reference) => at = &reference.expr,
                Expr::Paren(paren) => at = &paren.expr,
                Expr::MethodCall(call)
                    if call.args.is_empty()
                        && ["to_string", "as_str", "as_ref", "to_owned", "into", "clone"]
                            .contains(&call.method.to_string().as_str()) =>
                {
                    at = &call.receiver
                }
                Expr::Call(call)
                    if call.args.len() == 1
                        && matches!(&*call.func, Expr::Path(p) if p.path.segments.len() == 2 && p.path.segments[0].ident == "String") =>
                {
                    at = &call.args[0]
                }
                _ => break,
            }
        }
        self.refuse(
            arg.span(),
            "A key that is not text in the code",
            "Write the key as text in the step, or as a setting that the pipeline gives as text",
        );
        None
    }

    /// `payload.get(K).and_then(Value::as_x)` to the field, or None.
    fn typed_read(&mut self, expr: &Expr) -> Option<Expr> {
        let Expr::MethodCall(outer) = expr else {
            return None;
        };
        if outer.method != "and_then" || outer.args.len() != 1 {
            return None;
        }
        let Expr::MethodCall(get) = &*outer.receiver else {
            return None;
        };
        if get.method != "get" || get.args.len() != 1 || !self.is_payload(&get.receiver) {
            return None;
        }
        let key_type = Self::read_type(&outer.args[0])?;
        let key = self.key_of(&get.args[0])?;
        self.record(&key, Some(key_type), false, get.span());
        let payload = format_ident!("{}", self.payload);
        let field = format_ident!("{}", Self::field_of(&key));
        Some(match key_type {
            KeyType::Text => syn::parse_quote!(#payload.#field.as_deref()),
            _ => syn::parse_quote!(#payload.#field),
        })
    }

    /// A method of the Payload: has, insert or remove. `expr` is the call.
    fn payload_call(&mut self, expr: &mut Expr) {
        let Expr::MethodCall(call) = expr else { return };
        let method = call.method.to_string();
        let span = call.span();
        let payload = format_ident!("{}", self.payload);
        match (method.as_str(), call.args.len()) {
            ("has", 1) => {
                let Some(key) = self.key_of(&call.args[0]) else { return };
                self.record(&key, None, false, span);
                let field = format_ident!("{}", Self::field_of(&key));
                *expr = syn::parse_quote!(#payload.#field.is_some());
            }
            ("insert" | "remove", _) if !self.writes => {
                self.refuse(span, format!("`{}.{method}(..)` in a step that only reads", self.payload), "Only a Filter writes");
            }
            ("insert", 2) => {
                let Some(key) = self.key_of(&call.args[0]) else { return };
                let mut value = call.args[1].clone();
                self.visit_expr_mut(&mut value);
                let key_type = Self::written_type(&value);
                self.record(&key, key_type, key_type.is_none(), span);
                let field = format_ident!("{}", Self::field_of(&key));
                *expr = syn::parse_quote!(#payload.#field = Some(::core::convert::Into::into(#value)));
            }
            ("remove", 1) => {
                let Some(key) = self.key_of(&call.args[0]) else { return };
                self.record(&key, None, false, span);
                let field = format_ident!("{}", Self::field_of(&key));
                *expr = syn::parse_quote!(#payload.#field = None);
            }
            ("get", _) => self.refuse(span, format!("A read with no type: `{}.get(..)`", self.payload), "Read a key with .and_then(Value::as_f64), .and_then(Value::as_bool) or .and_then(Value::as_str)"),
            _ => {
                let shown = call.to_token_stream().to_string().replace(" . ", ".").replace(" (", "(").replace("( ", "(").replace(" )", ")");
                self.refuse(span, format!("`{shown}` is not in plain data"), USE_ONLY);
            }
        }
    }

    /// The names that must not be left in the compiled function: the Payload, `self` and `Value`.
    pub fn check_left(&mut self, tokens: TokenStream) {
        for tree in tokens {
            match tree {
                TokenTree::Ident(ident) if ident == self.payload.as_str() => {}
                TokenTree::Ident(ident) if ident == "self" => self.refuse(
                    ident.span(),
                    "`self` used in another way",
                    "Use self only to read a setting: self.field",
                ),
                TokenTree::Ident(ident) if ident == "Value" || ident == "Payload" => self.refuse(
                    ident.span(),
                    format!("`{ident}` used in another way"),
                    USE_ONLY,
                ),
                TokenTree::Group(group) => self.check_left(group.stream()),
                _ => {}
            }
        }
    }
}

// cup: allow-plain the rewrite of a step body: a walk of its syntax tree, called by LowerStepsFilter
impl VisitMut for PayloadRewriter<'_> {
    fn visit_expr_mut(&mut self, expr: &mut Expr) {
        if self.refusal.is_some() {
            return;
        }
        if let Some(read) = self.typed_read(expr) {
            *expr = read;
            return;
        }
        match expr {
            Expr::Field(field) if Self::is_self(&field.base) => {
                let Member::Named(name) = &field.member else {
                    return;
                };
                match self.settings.iter().find(|(setting, _)| name == setting) {
                    Some((setting, value)) => *expr = self.setting(setting, value),
                    None => {
                        let span = field.span();
                        self.refuse(
                            span,
                            format!("`self.{name}` is not a setting that the pipeline gives"),
                            "Give each setting in the call that makes the step",
                        );
                    }
                }
                return;
            }
            Expr::MethodCall(call) if Self::is_self(&call.receiver) => {
                let span = call.span();
                let method = call.method.to_string();
                self.refuse(
                    span,
                    format!("A step that calls a method of its own: `self.{method}()`"),
                    "Put the code of the step in its method",
                );
                return;
            }
            Expr::MethodCall(call) if matches!(&*call.receiver, Expr::MethodCall(inner) if self.is_payload(&inner.receiver) && (inner.method == "insert" || inner.method == "remove")) =>
            {
                let span = call.span();
                self.refuse(
                    span,
                    "A chain of writes on the Payload",
                    "Write one key in each statement",
                );
                return;
            }
            Expr::MethodCall(call) if self.is_payload(&call.receiver) => {
                self.payload_call(expr);
                return;
            }
            Expr::Path(path) if path.path.is_ident(&self.payload) => {
                let span = path.span();
                self.refuse(span, "The Payload given to other code", USE_ONLY);
                return;
            }
            _ => {}
        }
        visit_mut::visit_expr_mut(self, expr);
    }

    /// The arguments of a macro such as format! or println! are code too: they are read and rewritten.
    fn visit_macro_mut(&mut self, mac: &mut syn::Macro) {
        if self.refusal.is_some() {
            return;
        }
        match mac.parse_body_with(Punctuated::<Expr, Token![,]>::parse_terminated) {
            Ok(mut args) => {
                for arg in args.iter_mut() {
                    self.visit_expr_mut(arg);
                }
                mac.tokens = args.to_token_stream();
            }
            Err(_) => {
                let names = mac.tokens.to_string();
                if names
                    .split(|c: char| !c.is_alphanumeric() && c != '_')
                    .any(|word| word == self.payload || word == "self")
                {
                    let span = mac.span();
                    self.refuse(
                        span,
                        "A macro whose code the compiler cannot read uses the Payload or self",
                        "Read the Payload into a name first, and give the name to the macro",
                    );
                }
            }
        }
    }
}

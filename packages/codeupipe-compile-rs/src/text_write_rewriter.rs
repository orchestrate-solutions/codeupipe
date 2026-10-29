use syn::visit_mut::{self, VisitMut};
use syn::{Expr, Member};

/// Makes each write of a text key own its text: `payload.k = Some(v)`
/// becomes `payload.k = Some(Cow::Owned(v))`. The field of a text key
/// borrows the caller's text until a step writes it.
pub struct TextWriteRewriter<'a> {
    /// The name of the parameter of the step.
    pub payload: String,
    /// The fields of the text keys.
    pub fields: &'a [String],
}

// cup: allow-plain the rewrite of a step function: a walk of its syntax tree, called by BorrowTextFilter
impl TextWriteRewriter<'_> {
    /// True for `payload.k`, with `k` a text field.
    fn is_text_field(&self, expr: &Expr) -> bool {
        let Expr::Field(field) = expr else {
            return false;
        };
        let Member::Named(name) = &field.member else {
            return false;
        };
        matches!(&*field.base, Expr::Path(path) if path.path.is_ident(&self.payload))
            && self.fields.iter().any(|text| name == text)
    }
}

// cup: allow-plain the rewrite of a step function: a walk of its syntax tree, called by BorrowTextFilter
impl VisitMut for TextWriteRewriter<'_> {
    fn visit_expr_mut(&mut self, expr: &mut Expr) {
        if let Expr::Assign(assign) = expr {
            if self.is_text_field(&assign.left) {
                // PayloadRewriter writes a key as `Some(..)`, and removes it as `None`.
                if let Expr::Call(some) = &mut *assign.right {
                    if let Some(value) = some.args.first_mut() {
                        let written = value.clone();
                        *value = syn::parse_quote!(::std::borrow::Cow::Owned(#written));
                    }
                }
                return;
            }
        }
        visit_mut::visit_expr_mut(self, expr);
    }
}

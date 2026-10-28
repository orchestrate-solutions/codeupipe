use syn::visit::{self, Visit};

/// Whether `node` has a decision or a loop: `if`, `match`, `for`, `while`,
/// `loop`, or `let ... else`. A loop that is a method call (`map`,
/// `filter`, `for_each`), `&&`, `||` and `?` are not seen, and nor is code
/// in a macro call.
///
/// `walk` gives the visitor the node: `has_logic(|v| v.visit_block(block))`.
pub fn has_logic(walk: impl FnOnce(&mut LogicVisitor)) -> bool {
    let mut visitor = LogicVisitor { found: false };
    walk(&mut visitor);
    visitor.found
}

pub struct LogicVisitor {
    found: bool,
}

impl<'ast> Visit<'ast> for LogicVisitor {
    fn visit_expr_if(&mut self, _: &'ast syn::ExprIf) {
        self.found = true;
    }

    fn visit_expr_match(&mut self, _: &'ast syn::ExprMatch) {
        self.found = true;
    }

    fn visit_expr_for_loop(&mut self, _: &'ast syn::ExprForLoop) {
        self.found = true;
    }

    fn visit_expr_while(&mut self, _: &'ast syn::ExprWhile) {
        self.found = true;
    }

    fn visit_expr_loop(&mut self, _: &'ast syn::ExprLoop) {
        self.found = true;
    }

    fn visit_local(&mut self, local: &'ast syn::Local) {
        let diverges = local
            .init
            .as_ref()
            .is_some_and(|init| init.diverge.is_some());
        self.found |= diverges;
        visit::visit_local(self, local);
    }
}

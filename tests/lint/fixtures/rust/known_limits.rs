// What the lexical scan cannot see (documented in packages/codeupipe-lint/README.md). Each case
// is a real anonymous step that is NOT flagged (a false negative), or a
// named step that IS flagged (a false positive), so a change in behaviour
// shows up here.

pub fn false_negatives() -> Pipeline {
    // A closure factory defined in another file: its return type is unknown here.
    let p = Pipeline::new().add_filter(Box::new(other_module::make_closure()), "remote factory");
    // A closure stored in a struct field, then passed on.
    let holder = Holder { f: |_: &Payload| true };
    let p = p.add_filter(Box::new(Valve::new("v", Box::new(Named), holder.f)), "field");
    // A macro that expands to a closure.
    let p = p.add_filter(Box::new(Valve::new("v", Box::new(Named), pred!())), "macro");
    p
}

use crate::filters::Local;

pub fn false_positive_block_scope() -> Pipeline {
    let _unused = || {
        struct Local;
    };
    // Scopes are flattened per function: the imported `Local` is taken for the
    // one declared in the closure's block.
    Pipeline::new().add_filter(Box::new(Local), "imported") // expect: CUP-A003 (false positive)
}

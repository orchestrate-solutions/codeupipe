//! Step identity, derived from the code (conformance/API.md, "Step identity").
//!
//! A step is identified by the type path of the code that runs it,
//! `std::any::type_name::<F>()` captured where the step is added
//! (`my_crate::filters::Validate`). `add_*` are generic so the concrete type
//! is known; a `Box<dyn Filter>` does not implement `Filter`, so passing one
//! is a compile error.
//!
//! Refused here (a panic, like any other mistake in a pipeline's blueprint):
//! closures (`{{closure}}`) and types that name no concrete filter (a trait
//! object inside a generic wrapper). A struct declared inside a function has
//! an ordinary-looking path (`crate::f::Local`), so the linter catches that.
//!
//! `type_name` is documented as best-effort across compiler versions: pin
//! the toolchain, since an upgrade can change identities.

const FIX: &str = "Declare it as a named type (a struct implementing the trait) or, for a Valve predicate, \
a named fn or a struct implementing Predicate, so it has a stable identity and can be tested on its own.";

/// The identity of `T`, or a panic naming why it has none.
pub(crate) fn identify<T: ?Sized>(what: &str) -> String {
    let name = std::any::type_name::<T>();
    if name.contains("{{closure}}") {
        panic!("codeupipe: AnonymousStep: {what} is a closure ({name}). {FIX}");
    }
    if name.contains("dyn ") {
        panic!("codeupipe: AnonymousStep: {what} is type-erased ({name}): pass the concrete filter. {FIX}");
    }
    name.to_string()
}

/// `file:line` of a caller location (extra detail, not identity).
pub(crate) fn site(location: &std::panic::Location<'_>) -> String {
    format!("{}:{}", location.file(), location.line())
}

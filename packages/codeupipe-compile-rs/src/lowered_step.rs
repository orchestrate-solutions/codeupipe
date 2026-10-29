use crate::step::Role;

/// A step as a plain function of the compiled module.
#[derive(Clone)]
pub struct LoweredStep {
    pub role: Role,
    pub name: String,
    pub type_name: String,
    pub item: syn::ItemFn,
}

use proc_macro2::TokenStream;
use quote::quote;

/// The type of a key in the compiled struct: a number (`f64`), true or
/// false (`bool`), or text (`String`). Each field is an `Option`, because a
/// Payload can lack a key.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum KeyType {
    Number,
    Bool,
    Text,
}

// cup: allow-plain a value of the compiler: its name in a message, and its type in Rust
impl KeyType {
    pub fn name(self) -> &'static str {
        match self {
            KeyType::Number => "a number",
            KeyType::Bool => "true or false",
            KeyType::Text => "text",
        }
    }

    pub fn rust(self) -> TokenStream {
        match self {
            KeyType::Number => quote!(f64),
            KeyType::Bool => quote!(bool),
            KeyType::Text => quote!(String),
        }
    }
}

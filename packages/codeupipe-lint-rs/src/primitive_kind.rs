use std::collections::HashMap;
use std::path::Path;

use proc_macro2::Span;
use syn::spanned::Spanned;
use syn::{Attribute, Item, Meta, Type};

/// The primitives that a type can be. A type is a primitive when it
/// implements the trait: `impl Filter for DiscountFilter`. A named pipeline
/// implements `NamedPipeline`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum PrimitiveKind {
    Pipeline,
    Hook,
    Filter,
    Tap,
    Predicate,
}

// cup: allow-plain shared by the analysis Filters: it says which primitive a type is, from its trait
impl PrimitiveKind {
    /// The kind of the trait at the end of `path` (`codeupipe::Filter<Order>` is a Filter).
    pub fn of_trait(path: &syn::Path) -> Option<PrimitiveKind> {
        let name = path.segments.last()?.ident.to_string();
        [
            ("NamedPipeline", PrimitiveKind::Pipeline),
            ("Hook", PrimitiveKind::Hook),
            ("Filter", PrimitiveKind::Filter),
            ("Tap", PrimitiveKind::Tap),
            ("Predicate", PrimitiveKind::Predicate),
        ]
        .into_iter()
        .find(|(trait_name, _)| *trait_name == name)
        .map(|(_, kind)| kind)
    }

    /// The role word: `Filter`, `Pipeline`, ...
    pub fn name(self) -> &'static str {
        match self {
            PrimitiveKind::Pipeline => "Pipeline",
            PrimitiveKind::Hook => "Hook",
            PrimitiveKind::Filter => "Filter",
            PrimitiveKind::Tap => "Tap",
            PrimitiveKind::Predicate => "Predicate",
        }
    }
}

/// A type at the top level of a file that is a primitive.
pub struct Primitive {
    pub name: String,
    pub kind: PrimitiveKind,
    /// The name in the declaration of the type, or in the first `impl` of a
    /// primitive trait when the type is declared in another file.
    pub at: Span,
}

/// The name of the type that an `impl` is for: `DiscountFilter` for
/// `impl Filter for DiscountFilter` and for `impl<P> Filter<P> for DiscountFilter<P>`.
// cup: allow-plain shared by the analysis Filters: it says which primitive a type is, from its trait
pub fn self_type_name(self_ty: &Type) -> Option<String> {
    match self_ty {
        Type::Path(path) => path.path.segments.last().map(|s| s.ident.to_string()),
        _ => None,
    }
}

/// The primitives among `items`, in the order of the file. A type that
/// implements two primitive traits is one primitive, of the first kind of
/// Pipeline, Hook, Filter, Tap, Predicate.
// cup: allow-plain shared by the analysis Filters: it says which primitive a type is, from its trait
pub fn primitives_in(items: &[Item]) -> Vec<Primitive> {
    let mut declared = HashMap::new();
    let mut found: Vec<Primitive> = Vec::new();
    for item in items
        .iter()
        .filter(|item| !is_test_only(attributes_of(item)))
    {
        match item {
            Item::Struct(item) => {
                declared.insert(item.ident.to_string(), item.ident.span());
            }
            Item::Enum(item) => {
                declared.insert(item.ident.to_string(), item.ident.span());
            }
            Item::Impl(item) => {
                let kind = item
                    .trait_
                    .as_ref()
                    .and_then(|(_, path, _)| PrimitiveKind::of_trait(path));
                let (Some(kind), Some(name)) = (kind, self_type_name(&item.self_ty)) else {
                    continue;
                };
                match found.iter_mut().find(|primitive| primitive.name == name) {
                    Some(primitive) => primitive.kind = primitive.kind.min(kind),
                    None => found.push(Primitive {
                        name,
                        kind,
                        at: item.self_ty.span(),
                    }),
                }
            }
            _ => {}
        }
    }
    for primitive in &mut found {
        if let Some(at) = declared.get(&primitive.name) {
            primitive.at = *at;
        }
    }
    found.sort_by_key(|primitive| {
        let start = primitive.at.start();
        (start.line, start.column)
    });
    found
}

/// The names of the types that are primitives, at any level of the file.
// cup: allow-plain shared by the analysis Filters: it says which primitive a type is, from its trait
pub fn primitive_names(items: &[Item], out: &mut Vec<String>) {
    for item in items {
        match item {
            Item::Impl(item) => {
                let is_primitive = item
                    .trait_
                    .as_ref()
                    .and_then(|(_, path, _)| PrimitiveKind::of_trait(path))
                    .is_some();
                out.extend(self_type_name(&item.self_ty).filter(|_| is_primitive));
            }
            Item::Mod(item) => {
                if let Some((_, items)) = &item.content {
                    primitive_names(items, out);
                }
            }
            _ => {}
        }
    }
}

/// A file under a `tests` directory: an integration test of Cargo.
pub fn is_test_file(path: &str) -> bool {
    let path = Path::new(path);
    path.parent()
        .is_some_and(|parent| parent.components().any(|part| part.as_os_str() == "tests"))
}

/// The attributes of an item.
// cup: allow-plain shared by the analysis Filters: it says which primitive a type is, from its trait
pub fn attributes_of(item: &Item) -> &[Attribute] {
    match item {
        Item::Const(item) => &item.attrs,
        Item::Enum(item) => &item.attrs,
        Item::Fn(item) => &item.attrs,
        Item::Impl(item) => &item.attrs,
        Item::Mod(item) => &item.attrs,
        Item::Static(item) => &item.attrs,
        Item::Struct(item) => &item.attrs,
        Item::Trait(item) => &item.attrs,
        Item::Type(item) => &item.attrs,
        Item::Union(item) => &item.attrs,
        Item::Use(item) => &item.attrs,
        _ => &[],
    }
}

/// `#[test]`, or `#[cfg(test)]` and the like: code for the tests only.
// cup: allow-plain shared by the analysis Filters: it says which primitive a type is, from its trait
pub fn is_test_only(attributes: &[Attribute]) -> bool {
    attributes.iter().any(|attribute| match &attribute.meta {
        Meta::Path(path) => path.is_ident("test"),
        Meta::List(list) => {
            list.path.is_ident("cfg")
                && list
                    .tokens
                    .clone()
                    .into_iter()
                    .any(|token| token.to_string() == "test")
        }
        Meta::NameValue(_) => false,
    })
}

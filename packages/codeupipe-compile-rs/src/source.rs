/// One parsed file.
#[derive(Clone)]
pub struct Source {
    pub path: String,
    pub tree: syn::File,
}

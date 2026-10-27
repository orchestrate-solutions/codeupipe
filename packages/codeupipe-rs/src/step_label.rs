/// The label of a step: the name of its type, without its path and without
/// generic arguments. `my_app::pricing::DiscountFilter` gives `DiscountFilter`.
pub(crate) fn label_of<T: ?Sized>() -> String {
    let full = std::any::type_name::<T>();
    let path = full.split('<').next().unwrap_or(full);
    path.rsplit("::").next().unwrap_or(path).to_string()
}

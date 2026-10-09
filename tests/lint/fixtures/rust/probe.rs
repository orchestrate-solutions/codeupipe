// Step-identity probe cases, with describe(label, &f) replaced by
// a pipeline add call: the probe's cases as lint fixtures.
mod filters {
    pub struct Validate;
    pub fn normalize(p: i32) -> i32 { p }
}

fn make_closure(k: i32) -> impl Fn(i32) -> i32 { move |p| p + k }

fn main() {
    struct Local;
    let p = Pipeline::new()
        .add_filter(Box::new(filters::Validate), "struct")
        .add_filter(Box::new(filters::Validate), "same struct again")
        .add_filter(Box::new(Valve::new("v", Box::new(filters::Validate), filters::normalize)), "module function")
        .add_filter(Box::new(|p: i32| p), "closure literal") // expect: CUP-A001
        .add_filter(Box::new(make_closure(1)), "returned closure") // expect: CUP-A001
        .add_filter(Box::new(Local), "struct defined in a function"); // expect: CUP-A003
}

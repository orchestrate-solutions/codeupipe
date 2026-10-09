// Anonymous steps the Rust analyzer must flag (expect: comments name the rule).
use codeupipe_core::{Filter, Payload, Pipeline, Valve};

pub struct Named;
impl Filter for Named {
    fn call(&self, p: Payload) -> Result<Payload, Error> { Ok(p) }
}

fn is_on(_: &Payload) -> bool { true }

fn make_closure(k: i32) -> impl Fn(&Payload) -> bool { move |_p| k > 0 }

fn make_boxed() -> Box<dyn Fn(&Payload) -> bool> { Box::new(|_p| true) }

fn make_local() -> Box<dyn Filter> {
    struct Hidden;
    impl Filter for Hidden {
        fn call(&self, p: Payload) -> Result<Payload, Error> { Ok(p) }
    }
    Box::new(Hidden)
}

fn build_child() -> Result<Pipeline, String> {
    let p = Pipeline::new().add_filter(Box::new(Named), "n");
    Ok(p)
}

pub fn build() -> Result<Pipeline, String> {
    struct Local;
    impl Filter for Local {
        fn call(&self, p: Payload) -> Result<Payload, Error> { Ok(p) }
    }
    struct Tuple(i32);
    enum Mode { A }
    fn nested_pred(_: &Payload) -> bool { true }

    let p = Pipeline::new()
        .add_filter(Box::new(Local), "local") // expect: CUP-A003
        .add_filter(Box::new(Tuple(1)), "tuple") // expect: CUP-A003
        .add_tap(Box::new(Local {}), "tap") // expect: CUP-A003
        .add_filter(Box::new(Valve::new("v", Box::new(Named), |_| true)), "v") // expect: CUP-A001
        .add_filter(Box::new(Valve::new("v", Box::new(Named), move |_p: &Payload| false)), "v2") // expect: CUP-A001
        .add_filter(Box::new(Valve::new("v", Box::new(Local), is_on)), "v3") // expect: CUP-A003
        .add_filter(Box::new(Valve::new("v", Box::new(Named), nested_pred)), "v4") // expect: CUP-A002
        .add_filter(Box::new(Valve::new("v", Box::new(Named), make_closure(1))), "v5") // expect: CUP-A001
        .add_filter(Box::new(Valve::new("v", Box::new(Named), make_boxed())), "v6") // expect: CUP-A001
        .add_filter(make_local(), "factory") // expect: CUP-A003
        .add_parallel(vec![Box::new(Named), Box::new(Local)], "fan"); // expect: CUP-A003

    let pred = |_: &Payload| true;
    let bound = Local;
    let child = build_child()?;
    let p = p
        .add_filter(Box::new(Valve::new("v", Box::new(Named), pred)), "bound") // expect: CUP-A001
        .add_filter(Box::new(bound), "bound local") // expect: CUP-A003
        .add_pipeline(child, "child") // expect: CUP-A005
        .add_pipeline(Pipeline::new().add_filter(Box::new(Named), "x"), "inline"); // expect: CUP-A005
    let p = p.add_parallel(Parallel::new().with(Named).with(Local)); // expect: CUP-A003
    let _ = Mode::A;
    Ok(p)
}

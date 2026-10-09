// Named steps the Rust analyzer must NOT flag.
use codeupipe_core::{Filter, Payload, Pipeline, Valve};

pub struct Named(&'static str);
impl Filter for Named {
    fn call(&self, p: Payload) -> Result<Payload, Error> {
        let label = 'x'; // a char literal
        let _s = "a string with |x| a closure-looking text and struct Fake {";
        let _r = r#"raw "string" with add_filter(|p| p)"#;
        Ok(p)
    }
}

pub struct Onboarding(Pipeline);

fn is_on<'a>(_: &'a Payload) -> bool { true }
fn make_named() -> Box<dyn Filter> { Box::new(Named("m")) }

/* block comment: p.add_filter(Box::new(|p| p), "x") /* nested */ still a comment */
pub fn build(steps: Vec<Box<dyn Filter>>) -> Pipeline {
    // p.add_filter(Box::new(Local), "commented out")
    let mut p = Pipeline::new() // a plain pipeline at the top level is fine
        .add_filter(Box::new(Named("a")), "a")
        .add_tap(Box::new(Named("t")), "t")
        .add_filter(Box::new(Valve::new("v", Box::new(Named("b")), is_on)), "v")
        .add_parallel(vec![Box::new(Named("c")), Box::new(Named("d"))], "fan")
        .add_filter(make_named(), "factory");
    for s in steps {
        p = p.add_filter(s, "loop");
    }
    let _cap = String::with_capacity(4).len(); // `.with` off a Parallel chain is not a step
    let p = p.add_parallel(Parallel::new().with(Named("e")).with(Named("f")));
    let doubled: Vec<i32> = vec![1, 2].iter().map(|x| x * 2).collect(); // a closure that is not a step
    let _ = doubled;
    p
}

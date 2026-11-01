/// A step of a pipeline of a layout: a name, or `valve: [Predicate, Filter]`
/// (conformance/ADD.md, "The steps").
#[derive(Clone, Debug, PartialEq)]
pub enum LayoutStep {
    Name(String),
    Valve(String, String),
}

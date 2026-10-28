use codeupipe::PipelineData;

/// The data of this pipeline: a struct in place of the Payload. Each step
/// below takes an `Order`, and the compiler checks every field it uses.
#[derive(Clone, Debug, PartialEq)]
pub struct Order {
    pub price: f64,
    pub qty: u32,
    pub bulk: bool,
}

impl Order {
    pub fn new(price: f64, qty: u32) -> Self {
        Order {
            price,
            qty,
            bulk: false,
        }
    }
}

/// The one line that lets a Pipeline carry an Order.
impl PipelineData for Order {}

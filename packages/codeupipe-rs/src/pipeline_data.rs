/// What a Pipeline carries from step to step.
///
/// `Payload` is the default: a map of JSON-shaped values that any developer
/// can read, and that every runtime of codeupipe has. A type of your own can
/// take its place, such as a struct with the fields that your steps use:
///
/// ```
/// use codeupipe::{Filter, Pipeline, PipelineData, StepError};
///
/// #[derive(Clone)]
/// struct Order { price: f64 }
///
/// impl PipelineData for Order {}
///
/// struct DiscountFilter;
///
/// impl Filter<Order> for DiscountFilter {
///     fn call(&self, order: &mut Order) -> Result<(), StepError> {
///         order.price *= 0.9;
///         Ok(())
///     }
/// }
///
/// let mut pipeline = Pipeline::new();
/// pipeline.add_filter(DiscountFilter);
/// assert_eq!(pipeline.run(&Order { price: 100.0 })?.price, 90.0);
/// # Ok::<(), StepError>(())
/// ```
///
/// The Filters, Predicates, Taps and Hooks of that pipeline then take the
/// type, and a step for another type is a compile error. The rules stay the
/// same: `run` works on a clone of the input, only a Filter writes, a Tap
/// failure is recorded and the run goes on.
pub trait PipelineData: Clone + 'static {
    /// Called after each step when lineage is on (`observe(_, true)`), with
    /// the label of the step. `Payload` keeps the labels; a type of your own
    /// keeps them only if it implements this.
    fn stamp(&mut self, _label: &str) {}
}

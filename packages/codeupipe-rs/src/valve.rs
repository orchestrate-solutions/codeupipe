use crate::filter::Filter;
use crate::predicate::Predicate;

/// Valve: joins a Predicate to a Filter. The Filter runs only when the
/// Predicate is true.
///
/// `Pipeline::add_valve(predicate, filter)` makes one. It is not a public name.
pub(crate) struct Valve<P> {
    pub(crate) predicate: Box<dyn Predicate<P>>,
    pub(crate) filter: Box<dyn Filter<P>>,
}

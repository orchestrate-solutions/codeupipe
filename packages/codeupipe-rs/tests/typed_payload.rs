// A pipeline over a type of your own. Payload is the default, a map that any
// developer can read; a struct can take its place, and then every step of
// that pipeline takes the struct.
use std::cell::RefCell;
use std::rc::Rc;

use codeupipe::{Filter, Hook, NamedPipeline, Pipeline, PipelineData, Predicate, StepError, Tap};

#[derive(Clone, Debug, Default, PartialEq)]
struct Order {
    price: f64,
    qty: u32,
    bulk: bool,
}

impl PipelineData for Order {}

struct DiscountFilter {
    rate: f64,
}

impl Filter<Order> for DiscountFilter {
    fn call(&self, order: &mut Order) -> Result<(), StepError> {
        order.price = (order.price * (1.0 - self.rate) * 100.0).round() / 100.0;
        Ok(())
    }
}

struct MarkBulkFilter;

impl Filter<Order> for MarkBulkFilter {
    fn call(&self, order: &mut Order) -> Result<(), StepError> {
        order.bulk = true;
        Ok(())
    }
}

struct RefuseFreeFilter;

impl Filter<Order> for RefuseFreeFilter {
    fn call(&self, order: &mut Order) -> Result<(), StepError> {
        if order.price <= 0.0 {
            return Err("an order must cost something".into());
        }
        Ok(())
    }
}

struct AtLeastPredicate {
    minimum: u32,
}

impl Predicate<Order> for AtLeastPredicate {
    fn test(&self, order: &Order) -> bool {
        order.qty >= self.minimum
    }
}

struct SeeTap {
    seen: Rc<RefCell<Vec<f64>>>,
}

impl Tap<Order> for SeeTap {
    fn observe(&self, order: &Order) -> Result<(), StepError> {
        self.seen.borrow_mut().push(order.price);
        Ok(())
    }
}

#[derive(Clone, Default)]
struct RecordHook {
    events: Rc<RefCell<Vec<String>>>,
}

impl Hook<Order> for RecordHook {
    fn before(&self, step: Option<&str>, _order: &Order) {
        self.events
            .borrow_mut()
            .push(format!("before:{}", step.unwrap_or("")));
    }
    fn on_error(&self, step: Option<&str>, _error: &StepError, order: &Order) {
        self.events
            .borrow_mut()
            .push(format!("error:{}:{}", step.unwrap_or(""), order.price));
    }
}

struct PricingPipeline;

impl NamedPipeline<Order> for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline<Order>) {
        pipeline.add_filter(DiscountFilter { rate: 0.1 });
        pipeline.add_valve(AtLeastPredicate { minimum: 10 }, MarkBulkFilter);
    }
}

fn order(price: f64, qty: u32) -> Order {
    Order {
        price,
        qty,
        bulk: false,
    }
}

#[test]
fn every_primitive_takes_the_type() {
    let seen = Rc::new(RefCell::new(Vec::new()));
    let hook = RecordHook::default();
    let mut pipeline: Pipeline<Order> = Pipeline::new();
    pipeline.add_filter(DiscountFilter { rate: 0.1 });
    pipeline.add_valve(AtLeastPredicate { minimum: 10 }, MarkBulkFilter);
    pipeline.add_tap(SeeTap {
        seen: Rc::clone(&seen),
    });
    pipeline.use_hook(hook.clone());

    let input = order(100.0, 12);
    let out = pipeline.run(&input).unwrap();
    assert_eq!(
        out,
        Order {
            price: 90.0,
            qty: 12,
            bulk: true
        }
    );
    assert_eq!(input, order(100.0, 12)); // the caller's value is not changed
    assert_eq!(*seen.borrow(), [90.0]);
    assert_eq!(
        pipeline.state().executed(),
        ["DiscountFilter", "MarkBulkFilter", "SeeTap"]
    );
    assert_eq!(
        *hook.events.borrow(),
        ["before:", "before:DiscountFilter", "before:MarkBulkFilter"]
    );

    pipeline.run(&order(100.0, 2)).unwrap();
    assert_eq!(pipeline.state().skipped(), ["MarkBulkFilter"]);
}

#[test]
fn a_named_and_nested_pipeline_takes_the_type() {
    let mut pipeline = Pipeline::new();
    pipeline.add_pipeline(Pipeline::named(PricingPipeline));
    pipeline.add_filter(RefuseFreeFilter);
    let out = pipeline.run(&order(50.0, 10)).unwrap();
    assert_eq!(
        out,
        Order {
            price: 45.0,
            qty: 10,
            bulk: true
        }
    );
    assert_eq!(pipeline.labels(), ["PricingPipeline", "RefuseFreeFilter"]);
}

#[test]
fn a_failure_is_the_same_as_with_a_payload() {
    let hook = RecordHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(DiscountFilter { rate: 1.0 });
    pipeline.add_filter(RefuseFreeFilter);
    pipeline.use_hook(hook.clone());
    let error = pipeline.run(&order(10.0, 1)).unwrap_err();
    assert_eq!(error.to_string(), "an order must cost something");
    assert_eq!(pipeline.state().executed(), ["DiscountFilter"]);
    let events = hook.events.borrow();
    assert_eq!(
        events[events.len() - 2..],
        ["error:RefuseFreeFilter:0", "error::0"]
    );
}

#[derive(Clone, Default)]
struct Traced {
    steps: Vec<String>,
}
impl PipelineData for Traced {
    fn stamp(&mut self, label: &str) {
        self.steps.push(label.to_string());
    }
}
struct NoopFilter;
impl Filter<Traced> for NoopFilter {
    fn call(&self, _traced: &mut Traced) -> Result<(), StepError> {
        Ok(())
    }
}

#[test]
fn lineage_is_kept_only_by_a_type_that_keeps_it() {
    let mut traced = Pipeline::new();
    traced.add_filter(NoopFilter);
    traced.observe(false, true);
    assert_eq!(
        traced.run(&Traced::default()).unwrap().steps,
        ["NoopFilter"]
    );

    // Order does not keep lineage: with it on, the run is the same.
    let mut plain = Pipeline::new();
    plain.add_filter(MarkBulkFilter);
    plain.observe(true, true);
    assert!(plain.run(&order(1.0, 1)).unwrap().bulk);
    assert_eq!(plain.state().timings().len(), 1);
}

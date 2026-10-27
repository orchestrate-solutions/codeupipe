use std::marker::PhantomData;

use codeupipe::{Filter, NamedPipeline, Payload, Pipeline, Predicate, StepError, Tap, Value};

struct AddFilter;

impl Filter for AddFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let n = payload.get("n").and_then(Value::as_f64).unwrap_or(0.0);
        payload.insert("n", n + 1.0);
        Ok(())
    }
}

struct SeeTap;

impl Tap for SeeTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Ok(())
    }
}

struct IsOnPredicate;

impl Predicate for IsOnPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.get("on") == Some(&Value::Bool(true))
    }
}

struct InnerPipeline;

impl NamedPipeline for InnerPipeline {
    fn add_steps(&self, _pipeline: &mut Pipeline) {}
}

#[test]
fn the_label_is_the_name_of_the_type() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_tap(SeeTap);
    assert_eq!(pipeline.labels(), ["AddFilter", "SeeTap"]);
}

#[test]
fn the_second_use_of_a_type_gets_a_number() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_filter(AddFilter);
    pipeline.add_filter(AddFilter);
    assert_eq!(
        pipeline.labels(),
        ["AddFilter", "AddFilter#2", "AddFilter#3"]
    );
}

#[test]
fn a_valve_has_the_label_of_its_filter() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_valve(IsOnPredicate, AddFilter);
    assert_eq!(pipeline.labels(), ["AddFilter", "AddFilter#2"]);
}

#[test]
fn a_nested_pipeline_has_the_label_of_its_type() {
    let mut pipeline = Pipeline::new();
    pipeline.add_pipeline(Pipeline::named(InnerPipeline));
    pipeline.add_pipeline(Pipeline::new());
    assert_eq!(pipeline.labels(), ["InnerPipeline", "Pipeline"]);
}

#[test]
fn a_type_defined_in_a_function_works() {
    fn make() -> impl Filter {
        struct LocalFilter;
        impl Filter for LocalFilter {
            fn call(&self, _payload: &mut Payload) -> Result<(), StepError> {
                Ok(())
            }
        }
        LocalFilter
    }
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(make());
    assert_eq!(pipeline.labels(), ["LocalFilter"]);
}

#[test]
fn a_generic_type_has_its_name_without_the_arguments() {
    struct WrapFilter<T>(PhantomData<T>);
    impl<T> Filter for WrapFilter<T> {
        fn call(&self, _payload: &mut Payload) -> Result<(), StepError> {
            Ok(())
        }
    }
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(WrapFilter::<std::collections::HashMap<String, Vec<u8>>>(
        PhantomData,
    ));
    assert_eq!(pipeline.labels(), ["WrapFilter"]);
}

#[test]
fn labels_gives_a_new_list_each_time() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.labels().push("x".to_string());
    assert_eq!(pipeline.labels(), ["AddFilter"]);
}

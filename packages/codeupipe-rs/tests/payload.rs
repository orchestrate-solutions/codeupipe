use codeupipe::{Map, Payload, Value};

#[test]
fn the_map_that_the_caller_gives_is_copied() {
    let data = Map::from([("a", 1)]);
    let mut payload = Payload::from_map(data.clone());
    payload.insert("b", 2);
    assert_eq!(data, Map::from([("a", 1)]));
    assert_eq!(payload.to_dict(), Map::from([("a", 1), ("b", 2)]));
}

#[test]
fn an_empty_payload_has_no_keys() {
    assert_eq!(Payload::new().to_dict(), Map::new());
}

#[test]
fn get_gives_the_value_or_absent() {
    let payload = Payload::from_map(Map::from([("a", Value::from(1)), ("n", Value::Null)]));
    assert_eq!(payload.get("a"), Some(&Value::from(1)));
    assert_eq!(payload.get("missing"), None);
    // A default is the language's own: unwrap_or. A present null is not absent.
    assert_eq!(
        payload.get("missing").cloned().unwrap_or(Value::from(7)),
        Value::from(7)
    );
    assert_eq!(
        payload.get("n").cloned().unwrap_or(Value::from(7)),
        Value::Null
    );
}

#[test]
fn has_is_true_for_a_key_with_a_null_value() {
    let payload = Payload::from_map(Map::from([("n", Value::Null)]));
    assert!(payload.has("n"));
    assert!(!payload.has("missing"));
}

#[test]
fn insert_remove_merge_and_with_trace_change_the_payload_and_return_it() {
    let mut payload = Payload::from_map(Map::from([("a", 1)]));
    let other = Payload::from_map(Map::from([("c", 3)]));
    let returned: *const Payload = payload.insert("b", 2);
    assert!(std::ptr::eq(returned, &payload));
    let returned: *const Payload = payload.remove("a");
    assert!(std::ptr::eq(returned, &payload));
    let returned: *const Payload = payload.merge(&other);
    assert!(std::ptr::eq(returned, &payload));
    let returned: *const Payload = payload.with_trace("t-1");
    assert!(std::ptr::eq(returned, &payload));
    assert_eq!(payload.to_dict(), Map::from([("b", 2), ("c", 3)]));
    assert_eq!(payload.trace_id(), Some("t-1"));
}

#[test]
fn writes_chain() {
    let mut payload = Payload::new();
    payload.insert("a", 1).insert("b", 2).remove("a");
    assert_eq!(payload.to_dict(), Map::from([("b", 2)]));
}

#[test]
fn remove_of_a_key_that_is_not_there_does_nothing() {
    let mut payload = Payload::from_map(Map::from([("a", 1)]));
    payload.remove("zz");
    assert_eq!(payload.to_dict(), Map::from([("a", 1)]));
}

#[test]
fn in_a_merge_the_other_payload_wins() {
    let mut payload = Payload::from_map(Map::from([("a", 1), ("b", 1)]));
    payload.merge(&Payload::from_map(Map::from([("b", 2)])));
    assert_eq!(payload.to_dict(), Map::from([("a", 1), ("b", 2)]));
}

#[test]
fn a_merge_keeps_the_trace_id_it_has_and_takes_one_when_it_has_none() {
    let mut other = Payload::new();
    other.with_trace("other");

    let mut mine = Payload::new();
    mine.with_trace("mine").merge(&other);
    assert_eq!(mine.trace_id(), Some("mine"));

    let mut none = Payload::new();
    none.merge(&other);
    assert_eq!(none.trace_id(), Some("other"));
}

#[test]
fn copy_gives_a_separate_payload_with_the_same_contents() {
    let mut payload = Payload::from_map(Map::from([("a", 1)]));
    payload.with_trace("t-1");
    let mut copy = payload.copy();
    copy.insert("a", 2);
    assert_eq!(payload.get("a"), Some(&Value::from(1)));
    assert_eq!(copy.trace_id(), Some("t-1"));
}

#[test]
fn a_nested_value_changed_in_a_copy_is_not_changed_in_the_original() {
    // D6: copy() is deep in Rust. A shared value could not be changed in
    // place anyway, so the behaviour is the same as a shallow copy.
    let payload = Payload::from_map(Map::from([("list", Value::List(vec![Value::from(1)]))]));
    let mut copy = payload.copy();
    let mut list = copy
        .get("list")
        .and_then(Value::as_list)
        .unwrap_or(&[])
        .to_vec();
    list.push(Value::from(2));
    copy.insert("list", list);
    assert_eq!(
        payload.get("list"),
        Some(&Value::List(vec![Value::from(1)]))
    );
}

#[test]
fn to_dict_gives_a_new_map_each_time() {
    let payload = Payload::from_map(Map::from([("a", 1)]));
    let mut out = payload.to_dict();
    out.insert("a", 2);
    assert_eq!(payload.get("a"), Some(&Value::from(1)));
}

#[test]
fn the_trace_id_is_absent_until_it_is_set_and_the_lineage_starts_empty() {
    let payload = Payload::new();
    assert_eq!(payload.trace_id(), None);
    assert!(payload.lineage().is_empty());
}

#[test]
fn keys_keep_the_order_in_which_they_were_inserted() {
    let mut payload = Payload::new();
    payload
        .insert("b", 1)
        .insert("a", 2)
        .insert("c", 3)
        .remove("a");
    payload.insert("a", 4);
    let out = payload.to_dict();
    assert_eq!(out.keys().collect::<Vec<_>>(), ["b", "c", "a"]);
}

#[test]
fn numbers_compare_as_json_numbers_and_true_is_not_one() {
    assert_eq!(Value::from(1), Value::from(1.0));
    assert_ne!(Value::from(true), Value::from(1));
}

#[test]
fn maps_with_the_same_entries_are_equal_in_any_order() {
    assert_eq!(
        Map::from([("a", 1), ("b", 2)]),
        Map::from([("b", 2), ("a", 1)])
    );
    assert_ne!(Map::from([("a", 1)]), Map::from([("a", 1), ("b", 2)]));
}

#[test]
fn a_payload_can_go_to_another_thread() {
    fn send_and_sync<T: Send + Sync>() {}
    send_and_sync::<Payload>();
    send_and_sync::<codeupipe::Map>();
}

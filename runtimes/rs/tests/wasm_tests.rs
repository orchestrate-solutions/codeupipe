//! WASM integration tests for codeupipe-core.
//!
//! Run with: wasm-pack test --headless --chrome
//! Or:       wasm-pack test --node

#![cfg(feature = "wasm")]

use wasm_bindgen::prelude::*;
use wasm_bindgen_test::*;

wasm_bindgen_test_configure!(run_in_browser);

// We test via the JS API that wasm-bindgen generates.
// These tests verify the round-trip: JS object → Rust Payload → JS object.

#[wasm_bindgen_test]
fn payload_roundtrip() {
    // Create payload from a JS object
    let obj = js_sys::Object::new();
    js_sys::Reflect::set(&obj, &JsValue::from_str("name"), &JsValue::from_str("test")).unwrap();
    js_sys::Reflect::set(&obj, &JsValue::from_str("count"), &JsValue::from(42.0)).unwrap();

    let payload = codeupipe_core::wasm::WasmPayload::new(&obj.into());

    // Read values back
    assert_eq!(payload.get("name"), JsValue::from_str("test"));
    assert_eq!(payload.get("count"), JsValue::from(42.0));
    assert_eq!(payload.get("missing"), JsValue::UNDEFINED);
}

#[wasm_bindgen_test]
fn payload_insert_immutable() {
    let obj = js_sys::Object::new();
    js_sys::Reflect::set(&obj, &JsValue::from_str("x"), &JsValue::from(1.0)).unwrap();

    let p1 = codeupipe_core::wasm::WasmPayload::new(&obj.into());
    let p2 = p1.insert("y", &JsValue::from(2.0));

    // p1 should not have "y"
    assert_eq!(p1.get("y"), JsValue::UNDEFINED);
    // p2 should have both
    assert_eq!(p2.get("x"), JsValue::from(1.0));
    assert_eq!(p2.get("y"), JsValue::from(2.0));
}

#[wasm_bindgen_test]
fn payload_to_dict() {
    let obj = js_sys::Object::new();
    js_sys::Reflect::set(&obj, &JsValue::from_str("a"), &JsValue::from(1.0)).unwrap();

    let payload = codeupipe_core::wasm::WasmPayload::new(&obj.into());
    let dict = payload.to_dict();

    assert!(dict.is_object());
    let val = js_sys::Reflect::get(&dict, &JsValue::from_str("a")).unwrap();
    assert_eq!(val, JsValue::from(1.0));
}

#[wasm_bindgen_test]
fn payload_merge() {
    let obj1 = js_sys::Object::new();
    js_sys::Reflect::set(&obj1, &JsValue::from_str("a"), &JsValue::from(1.0)).unwrap();

    let obj2 = js_sys::Object::new();
    js_sys::Reflect::set(&obj2, &JsValue::from_str("b"), &JsValue::from(2.0)).unwrap();
    js_sys::Reflect::set(&obj2, &JsValue::from_str("a"), &JsValue::from(99.0)).unwrap();

    let p1 = codeupipe_core::wasm::WasmPayload::new(&obj1.into());
    let p2 = codeupipe_core::wasm::WasmPayload::new(&obj2.into());
    let merged = p1.merge(&p2);

    // b should exist, a should be overridden by p2
    assert_eq!(merged.get("b"), JsValue::from(2.0));
    assert_eq!(merged.get("a"), JsValue::from(99.0));
}

#[wasm_bindgen_test]
fn payload_trace_and_lineage() {
    let obj = js_sys::Object::new();
    let p = codeupipe_core::wasm::WasmPayload::new(&obj.into());

    assert_eq!(p.trace_id(), JsValue::UNDEFINED);
    assert_eq!(p.lineage().length(), 0);

    let p2 = p.with_trace("trace-123");
    assert_eq!(p2.trace_id(), JsValue::from_str("trace-123"));

    let p3 = p2.stamp("step1").stamp("step2");
    assert_eq!(p3.lineage().length(), 2);
}

#[wasm_bindgen_test]
fn mutable_payload() {
    let mut mp = codeupipe_core::wasm::WasmMutablePayload::new();
    mp.set("key", &JsValue::from_str("value"));
    assert_eq!(mp.get("key"), JsValue::from_str("value"));

    let immutable = mp.to_immutable();
    assert_eq!(immutable.get("key"), JsValue::from_str("value"));
}

#[wasm_bindgen_test]
fn pipeline_empty_run() {
    let obj = js_sys::Object::new();
    js_sys::Reflect::set(
        &obj,
        &JsValue::from_str("input"),
        &JsValue::from_str("data"),
    )
    .unwrap();

    let mut pipeline = codeupipe_core::wasm::WasmPipeline::new();
    let payload = codeupipe_core::wasm::WasmPayload::new(&obj.into());

    let result = pipeline.run(payload).unwrap();
    assert_eq!(result.get("input"), JsValue::from_str("data"));

    let state = pipeline.state();
    assert_eq!(state.executed().length(), 0);
    assert!(!state.has_errors());
}

#[wasm_bindgen_test]
fn pipeline_state_after_run() {
    let mut pipeline = codeupipe_core::wasm::WasmPipeline::new();
    pipeline.observe(true, false);

    // Add identity filter via JS closure
    let identity = js_sys::Function::new_with_args("payload", "return payload;");
    pipeline.add_filter("identity", identity);

    let obj = js_sys::Object::new();
    let payload = codeupipe_core::wasm::WasmPayload::new(&obj.into());
    let _result = pipeline.run(payload).unwrap();

    let state = pipeline.state();
    assert_eq!(state.executed().length(), 1);
    assert!(!state.has_errors());
}

#[wasm_bindgen_test]
fn pipeline_describe() {
    let mut pipeline = codeupipe_core::wasm::WasmPipeline::new();
    let noop = js_sys::Function::new_with_args("p", "return p;");
    pipeline.add_filter("step1", noop.clone());
    pipeline.add_filter("step2", noop);

    let desc = pipeline.describe();
    assert_eq!(desc.length(), 2);
}

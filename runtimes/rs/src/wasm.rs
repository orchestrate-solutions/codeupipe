//! WASM bindings for codeupipe-core.
//!
//! Exposes Payload, Pipeline, and State to JavaScript via wasm-bindgen.
//! Uses JsValue for dynamic data interchange — Rust's HashMap<String, Value>
//! becomes a JS object, and vice versa.
//!
//! Compiled only when `--features wasm` is active.

use js_sys;
use std::collections::HashMap;
use wasm_bindgen::prelude::*;

use crate::filter::Filter;
use crate::payload::{MutablePayload as RustMutablePayload, Payload as RustPayload, Value};
use crate::state::State as RustState;

// ---------------------------------------------------------------------------
// Value ↔ JsValue conversion
// ---------------------------------------------------------------------------

fn value_to_js(v: &Value) -> JsValue {
    match v {
        Value::Null => JsValue::NULL,
        Value::Bool(b) => JsValue::from(*b),
        Value::Int(i) => JsValue::from(*i as f64),
        Value::Float(f) => JsValue::from(*f),
        Value::Str(s) => JsValue::from_str(s),
        Value::List(items) => {
            let arr = js_sys::Array::new();
            for item in items {
                arr.push(&value_to_js(item));
            }
            arr.into()
        }
        Value::Map(map) => {
            let obj = js_sys::Object::new();
            for (k, v) in map {
                js_sys::Reflect::set(&obj, &JsValue::from_str(k), &value_to_js(v))
                    .unwrap_or_default();
            }
            obj.into()
        }
    }
}

fn js_to_value(v: &JsValue) -> Value {
    if v.is_null() || v.is_undefined() {
        Value::Null
    } else if let Some(b) = v.as_bool() {
        Value::Bool(b)
    } else if let Some(f) = v.as_f64() {
        // Distinguish int vs float
        if f.fract() == 0.0 && f >= i64::MIN as f64 && f <= i64::MAX as f64 {
            Value::Int(f as i64)
        } else {
            Value::Float(f)
        }
    } else if let Some(s) = v.as_string() {
        Value::Str(s)
    } else if js_sys::Array::is_array(v) {
        let arr = js_sys::Array::from(v);
        let items: Vec<Value> = arr.iter().map(|item| js_to_value(&item)).collect();
        Value::List(items)
    } else if v.is_object() {
        let obj = js_sys::Object::from(v.clone());
        let entries = js_sys::Object::entries(&obj);
        let mut map = HashMap::new();
        for i in 0..entries.length() {
            let entry = js_sys::Array::from(&entries.get(i));
            if let Some(key) = entry.get(0).as_string() {
                map.insert(key, js_to_value(&entry.get(1)));
            }
        }
        Value::Map(map)
    } else {
        Value::Null
    }
}

/// Convert a JS object { key: value, ... } into HashMap<String, Value>.
fn js_object_to_map(obj: &JsValue) -> HashMap<String, Value> {
    if !obj.is_object() || obj.is_null() {
        return HashMap::new();
    }
    let entries = js_sys::Object::entries(&js_sys::Object::from(obj.clone()));
    let mut map = HashMap::new();
    for i in 0..entries.length() {
        let entry = js_sys::Array::from(&entries.get(i));
        if let Some(key) = entry.get(0).as_string() {
            map.insert(key, js_to_value(&entry.get(1)));
        }
    }
    map
}

/// Convert HashMap<String, Value> into a JS object.
fn map_to_js_object(map: &HashMap<String, Value>) -> JsValue {
    let obj = js_sys::Object::new();
    for (k, v) in map {
        js_sys::Reflect::set(&obj, &JsValue::from_str(k), &value_to_js(v)).unwrap_or_default();
    }
    obj.into()
}

// ---------------------------------------------------------------------------
// WasmPayload — immutable data container
// ---------------------------------------------------------------------------

/// Immutable data container for pipeline processing.
/// Create with `WasmPayload.new(jsObject)`, read with `.get(key)`,
/// produce new payloads with `.insert(key, value)`.
#[wasm_bindgen(js_name = "Payload")]
pub struct WasmPayload {
    inner: RustPayload,
}

#[wasm_bindgen(js_class = "Payload")]
impl WasmPayload {
    /// Create a new Payload from a JS object.
    /// ```js
    /// const p = new Payload({ name: "test", count: 42 });
    /// ```
    #[wasm_bindgen(constructor)]
    pub fn new(data: &JsValue) -> WasmPayload {
        let map = js_object_to_map(data);
        WasmPayload {
            inner: RustPayload::from_data(map),
        }
    }

    /// Get a value by key. Returns undefined if not found.
    pub fn get(&self, key: &str) -> JsValue {
        match self.inner.get(key) {
            Some(v) => value_to_js(v),
            None => JsValue::UNDEFINED,
        }
    }

    /// Return a new Payload with the key set to value.
    /// The original payload is unchanged (immutable).
    pub fn insert(&self, key: &str, value: &JsValue) -> WasmPayload {
        WasmPayload {
            inner: self.inner.insert(key, js_to_value(value)),
        }
    }

    /// Alias for insert — same semantics, different name for type evolution.
    #[wasm_bindgen(js_name = "insertAs")]
    pub fn insert_as(&self, key: &str, value: &JsValue) -> WasmPayload {
        self.insert(key, value)
    }

    /// Return a new Payload with a trace ID attached.
    #[wasm_bindgen(js_name = "withTrace")]
    pub fn with_trace(&self, trace_id: &str) -> WasmPayload {
        WasmPayload {
            inner: self.inner.with_trace(trace_id),
        }
    }

    /// Record a processing step in lineage (internal).
    #[wasm_bindgen(js_name = "_stamp")]
    pub fn stamp(&self, step_name: &str) -> WasmPayload {
        WasmPayload {
            inner: self.inner.stamp(step_name),
        }
    }

    /// Merge another payload into this one.
    /// Returns a new payload — other's keys take precedence.
    pub fn merge(&self, other: &WasmPayload) -> WasmPayload {
        WasmPayload {
            inner: self.inner.merge(&other.inner),
        }
    }

    /// Convert to a mutable payload for bulk writes.
    #[wasm_bindgen(js_name = "withMutation")]
    pub fn with_mutation(self) -> WasmMutablePayload {
        WasmMutablePayload {
            inner: self.inner.with_mutation(),
        }
    }

    /// Return all data as a plain JS object.
    #[wasm_bindgen(js_name = "toDict")]
    pub fn to_dict(&self) -> JsValue {
        map_to_js_object(&self.inner.to_dict())
    }

    /// The trace ID, or undefined.
    #[wasm_bindgen(getter, js_name = "traceId")]
    pub fn trace_id(&self) -> JsValue {
        match self.inner.trace_id() {
            Some(t) => JsValue::from_str(t),
            None => JsValue::UNDEFINED,
        }
    }

    /// The lineage as a JS array of strings.
    #[wasm_bindgen(getter)]
    pub fn lineage(&self) -> js_sys::Array {
        let arr = js_sys::Array::new();
        for step in self.inner.lineage() {
            arr.push(&JsValue::from_str(step));
        }
        arr
    }

    /// Serialize payload to JSON bytes.
    pub fn serialize(&self) -> Vec<u8> {
        self.inner.serialize()
    }

    /// Deserialize payload from JSON bytes.
    pub fn deserialize(raw: &[u8]) -> Result<WasmPayload, JsError> {
        RustPayload::deserialize(raw)
            .map(|p| WasmPayload { inner: p })
            .map_err(|e| JsError::new(&e))
    }
}

// ---------------------------------------------------------------------------
// WasmMutablePayload — mutable variant
// ---------------------------------------------------------------------------

/// Mutable data container for bulk writes. Convert back to immutable
/// with `.toImmutable()`.
#[wasm_bindgen(js_name = "MutablePayload")]
pub struct WasmMutablePayload {
    inner: RustMutablePayload,
}

#[wasm_bindgen(js_class = "MutablePayload")]
impl WasmMutablePayload {
    /// Create a new empty MutablePayload.
    #[wasm_bindgen(constructor)]
    pub fn new() -> WasmMutablePayload {
        WasmMutablePayload {
            inner: RustMutablePayload::new(),
        }
    }

    /// Get a value by key.
    pub fn get(&self, key: &str) -> JsValue {
        match self.inner.get(key) {
            Some(v) => value_to_js(v),
            None => JsValue::UNDEFINED,
        }
    }

    /// Set a value in place. Mutates this payload.
    pub fn set(&mut self, key: &str, value: &JsValue) {
        self.inner.set(key, js_to_value(value));
    }

    /// Convert back to an immutable Payload.
    #[wasm_bindgen(js_name = "toImmutable")]
    pub fn to_immutable(self) -> WasmPayload {
        WasmPayload {
            inner: self.inner.to_immutable(),
        }
    }
}

// ---------------------------------------------------------------------------
// WasmState — pipeline execution metadata
// ---------------------------------------------------------------------------

/// Pipeline execution state — read-only view of what happened during run.
#[wasm_bindgen(js_name = "State")]
pub struct WasmState {
    inner: RustState,
}

#[wasm_bindgen(js_class = "State")]
impl WasmState {
    /// Filters that executed.
    #[wasm_bindgen(getter)]
    pub fn executed(&self) -> js_sys::Array {
        let arr = js_sys::Array::new();
        for s in &self.inner.executed {
            arr.push(&JsValue::from_str(s));
        }
        arr
    }

    /// Filters that were skipped.
    #[wasm_bindgen(getter)]
    pub fn skipped(&self) -> js_sys::Array {
        let arr = js_sys::Array::new();
        for s in &self.inner.skipped {
            arr.push(&JsValue::from_str(s));
        }
        arr
    }

    /// Whether any errors occurred.
    #[wasm_bindgen(getter, js_name = "hasErrors")]
    pub fn has_errors(&self) -> bool {
        self.inner.has_errors()
    }

    /// The last error message, or undefined.
    #[wasm_bindgen(getter, js_name = "lastError")]
    pub fn last_error(&self) -> JsValue {
        match self.inner.last_error() {
            Some(s) => JsValue::from_str(s),
            None => JsValue::UNDEFINED,
        }
    }

    /// Timing data as a JS object { filterName: seconds }.
    #[wasm_bindgen(getter)]
    pub fn timings(&self) -> JsValue {
        let obj = js_sys::Object::new();
        for (k, v) in &self.inner.timings {
            js_sys::Reflect::set(&obj, &JsValue::from_str(k), &JsValue::from(*v))
                .unwrap_or_default();
        }
        obj.into()
    }

    /// Error details as a JS array of [stepName, message] pairs.
    #[wasm_bindgen(getter)]
    pub fn errors(&self) -> js_sys::Array {
        let arr = js_sys::Array::new();
        for (name, msg) in &self.inner.errors {
            let pair = js_sys::Array::new();
            pair.push(&JsValue::from_str(name));
            pair.push(&JsValue::from_str(msg));
            arr.push(&pair);
        }
        arr
    }
}

// ---------------------------------------------------------------------------
// JsFilter — wraps a JS function as a Rust Filter
// ---------------------------------------------------------------------------

/// A Filter implemented as a JS callback function.
/// The JS function receives a WasmPayload and must return a WasmPayload.
struct JsFilter {
    callback: js_sys::Function,
}

impl Filter for JsFilter {
    fn call(
        &self,
        payload: RustPayload,
    ) -> Result<RustPayload, Box<dyn std::error::Error + Send + Sync>> {
        let wasm_payload = WasmPayload { inner: payload };
        let this = JsValue::NULL;
        let result = self.callback.call1(&this, &JsValue::from(wasm_payload));
        match result {
            Ok(val) => {
                // The JS function should return a Payload.
                // We need to extract the inner RustPayload.
                // Since wasm_bindgen generates JsCast for our types, we can try to downcast.
                // However, the JS function might return a plain object.
                // Strategy: if the returned value has a toDict method, it's a WasmPayload wrapper.
                // Otherwise, treat it as a plain JS object and construct a new Payload.
                if val.is_object() {
                    let to_dict = js_sys::Reflect::get(&val, &JsValue::from_str("__wbg_ptr"));
                    if to_dict.is_ok() && !to_dict.as_ref().unwrap().is_undefined() {
                        // It's a WasmPayload — extract via toDict and rebuild
                        let dict_fn = js_sys::Reflect::get(&val, &JsValue::from_str("toDict"));
                        if let Ok(func) = dict_fn {
                            if let Some(f) = func.dyn_ref::<js_sys::Function>() {
                                let dict = f.call0(&val).unwrap_or(JsValue::NULL);
                                let map = js_object_to_map(&dict);
                                return Ok(RustPayload::from_data(map));
                            }
                        }
                    }
                    // Fallback: treat as plain object
                    let map = js_object_to_map(&val);
                    Ok(RustPayload::from_data(map))
                } else {
                    Err("Filter callback must return a Payload or object".into())
                }
            }
            Err(e) => {
                let msg = e
                    .as_string()
                    .unwrap_or_else(|| "JS filter error".to_string());
                Err(msg.into())
            }
        }
    }

}

// JsFilter cannot truly be Send + Sync in WASM (single-threaded),
// but wasm-bindgen requires it for trait objects. WASM is single-threaded
// so this is safe.
unsafe impl Send for JsFilter {}
unsafe impl Sync for JsFilter {}

// ---------------------------------------------------------------------------
// WasmPipeline — orchestrator
// ---------------------------------------------------------------------------

/// Pipeline orchestrator — add filters, run, read state.
///
/// ```js
/// const pipeline = new Pipeline();
/// pipeline.addFilter("step1", (payload) => payload.insert("done", true));
/// const result = pipeline.run(new Payload({ input: "data" }));
/// console.log(pipeline.state.executed); // ["step1"]
/// ```
#[wasm_bindgen(js_name = "Pipeline")]
pub struct WasmPipeline {
    steps: Vec<(String, Box<dyn Filter>)>,
    state: RustState,
    observe_timing: bool,
    observe_lineage: bool,
}

#[wasm_bindgen(js_class = "Pipeline")]
impl WasmPipeline {
    /// Create a new empty Pipeline.
    #[wasm_bindgen(constructor)]
    pub fn new() -> WasmPipeline {
        WasmPipeline {
            steps: Vec::new(),
            state: RustState::new(),
            observe_timing: false,
            observe_lineage: false,
        }
    }

    /// Add a JS function as a filter step.
    ///
    /// The callback receives a `Payload` and must return a `Payload`.
    /// ```js
    /// pipeline.addFilter("validate", (payload) => {
    ///     if (!payload.get("email")) throw new Error("No email");
    ///     return payload.insert("valid", true);
    /// });
    /// ```
    #[wasm_bindgen(js_name = "addFilter")]
    pub fn add_filter(&mut self, name: &str, callback: js_sys::Function) {
        self.steps.push((
            name.to_string(),
            Box::new(JsFilter { callback }),
        ));
    }

    /// Enable observation features.
    pub fn observe(&mut self, timing: bool, lineage: bool) {
        self.observe_timing = timing;
        self.observe_lineage = lineage;
    }

    /// Execute the pipeline synchronously.
    /// Returns the final Payload after all filters have run.
    pub fn run(&mut self, initial: WasmPayload) -> Result<WasmPayload, JsError> {
        self.state = RustState::new();
        let mut payload = initial.inner;

        for (name, filter) in &self.steps {
            let t0 = web_sys::window()
                .and_then(|w| w.performance())
                .map(|p| p.now())
                .unwrap_or(0.0);

            match filter.call(payload.clone()) {
                Ok(result) => {
                    payload = result;
                    self.state.mark_executed(name);
                }
                Err(e) => {
                    let msg = e.to_string();
                    self.state.record_error(name, &msg);

                    if self.observe_timing {
                        let elapsed = web_sys::window()
                            .and_then(|w| w.performance())
                            .map(|p| p.now())
                            .unwrap_or(0.0)
                            - t0;
                        self.state.record_timing(name, elapsed / 1000.0);
                    }

                    return Err(JsError::new(&msg));
                }
            }

            if self.observe_timing {
                let elapsed = web_sys::window()
                    .and_then(|w| w.performance())
                    .map(|p| p.now())
                    .unwrap_or(0.0)
                    - t0;
                self.state.record_timing(name, elapsed / 1000.0);
            }

            if self.observe_lineage {
                payload = payload.stamp(name);
            }
        }

        Ok(WasmPayload { inner: payload })
    }

    /// Pipeline execution state — available after run().
    #[wasm_bindgen(getter)]
    pub fn state(&self) -> WasmState {
        WasmState {
            inner: self.state.clone(),
        }
    }

    /// Describe the pipeline structure as a JS array of { name, type } objects.
    pub fn describe(&self) -> js_sys::Array {
        let arr = js_sys::Array::new();
        for (name, _) in &self.steps {
            let obj = js_sys::Object::new();
            js_sys::Reflect::set(&obj, &JsValue::from_str("name"), &JsValue::from_str(name))
                .unwrap_or_default();
            js_sys::Reflect::set(
                &obj,
                &JsValue::from_str("type"),
                &JsValue::from_str("filter"),
            )
            .unwrap_or_default();
            arr.push(&obj);
        }
        arr
    }
}

// ---------------------------------------------------------------------------
// Module init
// ---------------------------------------------------------------------------

/// Initialize the WASM module. Call once on page load.
/// Sets up panic hook for better error messages in the console.
#[wasm_bindgen(start)]
pub fn init() {
    console_error_panic_hook::set_once();
}

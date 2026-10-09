//! Shape trade-off bench for Rust.
//!
//! Same 8-filter, 200k-iter hop shape, three payload/dispatch strategies:
//!   1. current      — Box<dyn Filter> + HashMap<String, Value>    (framework)
//!   2. static_hmap  — generic Filter trait  + HashMap<String, Value>
//!   3. static_typed — generic Filter trait  + struct { n: i64 }
//!   4. bare         — raw fn composition,  no framework at all
//!
//! Prints one JSON line per variant so the matrix script can pick it up.


use codeupipe_core::{Filter, Payload, Pipeline};
use std::hint::black_box;
use std::time::Instant;

const FILTERS: usize = 8;
const ITERS: usize = 200_000;

// ----- 1. current (baseline) ---------------------------------------------
struct DynInc;
impl Filter for DynInc {
    fn call(&self, p: Payload) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
        let n = p.get("n").and_then(|v| v.as_int()).unwrap_or(0);
        Ok(p.insert("n", (n + 1).into()))
    }
}

fn bench_current() -> f64 {
    let mut pipe = Pipeline::new();
    for _ in 0..FILTERS {
        pipe = pipe.add_filter(DynInc);
    }
    pipe = pipe.observe_state(false);
    let seed = Payload::new().insert("n", 0_i64.into());
    for _ in 0..1000 { let _ = pipe.run(seed.clone()); }
    let t0 = Instant::now();
    let mut out = seed.clone();
    for _ in 0..ITERS { out = pipe.run(seed.clone()).unwrap(); }
    black_box(&out);
    t0.elapsed().as_nanos() as f64 / (ITERS as f64) / (FILTERS as f64)
}

// ----- 2. static_hmap ----------------------------------------------------
// Same HashMap payload, but the filter chain is compile-time generic.
// Zero vtable dispatch, one alloc per hop remains.
trait GFilter { fn call(&self, p: Payload) -> Payload; }
struct GInc;
impl GFilter for GInc {
    fn call(&self, p: Payload) -> Payload {
        let n = p.get("n").and_then(|v| v.as_int()).unwrap_or(0);
        p.insert("n", (n + 1).into())
    }
}

fn bench_static_hmap() -> f64 {
    let f = GInc;
    let seed = Payload::new().insert("n", 0_i64.into());
    // warmup
    for _ in 0..1000 {
        let mut p = seed.clone();
        for _ in 0..FILTERS { p = f.call(p); }
        black_box(&p);
    }
    let t0 = Instant::now();
    let mut out = seed.clone();
    for _ in 0..ITERS {
        let mut p = seed.clone();
        for _ in 0..FILTERS { p = f.call(p); }
        out = p;
    }
    black_box(&out);
    t0.elapsed().as_nanos() as f64 / (ITERS as f64) / (FILTERS as f64)
}

// ----- 3. static_typed ---------------------------------------------------
// Compile-time generic + concrete struct payload. No allocation on hop.
#[derive(Clone, Copy)]
struct TypedPayload { n: i64 }
trait TFilter { fn call(&self, p: TypedPayload) -> TypedPayload; }
struct TInc;
impl TFilter for TInc {
    #[inline(always)]
    fn call(&self, mut p: TypedPayload) -> TypedPayload { p.n += 1; p }
}

fn bench_static_typed(start: i64) -> f64 {
    let f = TInc;
    let seed = TypedPayload { n: black_box(start) };
    for _ in 0..1000 {
        let mut p = seed;
        for _ in 0..FILTERS { p = f.call(p); }
        black_box(&p);
    }
    let t0 = Instant::now();
    let mut out = seed;
    for _ in 0..ITERS {
        let mut p = black_box(seed);
        for _ in 0..FILTERS { p = f.call(black_box(p)); }
        out = black_box(p);
    }
    black_box(&out);
    t0.elapsed().as_nanos() as f64 / (ITERS as f64) / (FILTERS as f64)
}

// ----- 4. bare -----------------------------------------------------------
// No framework. Raw function calls the compiler will happily inline.
#[inline(always)]
fn inc_bare(mut p: TypedPayload) -> TypedPayload { p.n += 1; p }

fn bench_bare(start: i64) -> f64 {
    let seed = TypedPayload { n: black_box(start) };
    for _ in 0..1000 {
        let mut p = seed;
        for _ in 0..FILTERS { p = inc_bare(p); }
        black_box(&p);
    }
    let t0 = Instant::now();
    let mut out = seed;
    for _ in 0..ITERS {
        let mut p = black_box(seed);
        for _ in 0..FILTERS { p = inc_bare(black_box(p)); }
        out = black_box(p);
    }
    black_box(&out);
    t0.elapsed().as_nanos() as f64 / (ITERS as f64) / (FILTERS as f64)
}


// ----- 5. dyn_typed ------------------------------------------------------
// Realistic ceiling for a TypedPipeline<Ctx> API:
// vtable dispatch (Box<dyn>) but the payload is a concrete struct.
trait DTFilter { fn call(&self, p: TypedPayload) -> TypedPayload; }
struct DTInc;
impl DTFilter for DTInc {
    fn call(&self, mut p: TypedPayload) -> TypedPayload { p.n += 1; p }
}

fn bench_dyn_typed(start: i64) -> f64 {
    let chain: Vec<Box<dyn DTFilter>> = (0..FILTERS).map(|_| Box::new(DTInc) as Box<dyn DTFilter>).collect();
    let seed = TypedPayload { n: black_box(start) };
    for _ in 0..1000 {
        let mut p = black_box(seed);
        for f in &chain { p = f.call(black_box(p)); }
        black_box(&p);
    }
    let t0 = Instant::now();
    let mut out = seed;
    for _ in 0..ITERS {
        let mut p = black_box(seed);
        for f in &chain { p = f.call(black_box(p)); }
        out = black_box(p);
    }
    black_box(&out);
    t0.elapsed().as_nanos() as f64 / (ITERS as f64) / (FILTERS as f64)
}

fn emit(variant: &str, ns_per_hop: f64) {
    println!(
        "{{\"runtime\":\"rust\",\"variant\":\"{}\",\"filters\":{},\"iterations\":{},\"ns_per_hop\":{:.2}}}",
        variant, FILTERS, ITERS, ns_per_hop
    );
}

fn main() {
    let start: i64 = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(0);
    emit("current",      bench_current());
    emit("static_hmap",  bench_static_hmap());
    emit("static_typed", bench_static_typed(start));
    emit("dyn_typed",    bench_dyn_typed(start));
    emit("bare",         bench_bare(start));
}

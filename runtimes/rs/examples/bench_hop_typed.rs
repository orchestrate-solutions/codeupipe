//! TypedPipeline<Ctx> hop bench.
//!
//! Same 8-filter, 200k-iter shape as bench_hop, using the typed API.
//! Emits JSON in the matrix schema.

use codeupipe_core::typed::{TypedFilter, TypedPipeline};
use std::hint::black_box;
use std::time::Instant;

#[derive(Clone, Copy)]
struct Ctx { n: i64 }

struct Inc;
impl TypedFilter<Ctx> for Inc {
    fn call(&self, mut c: Ctx) -> Result<Ctx, Box<dyn std::error::Error + Send + Sync>> {
        c.n += 1;
        Ok(c)
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let filters: i64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(8);
    let iters: i64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(200_000);

    let mut pipe: TypedPipeline<Ctx> = TypedPipeline::new();
    for i in 0..filters {
        pipe = pipe.add_filter(Inc, &format!("inc_{i}"));
    }
    pipe = pipe.observe_state(false);

    let seed = Ctx { n: 0 };
    for _ in 0..1000 {
        let _ = pipe.run(black_box(seed));
    }

    let t0 = Instant::now();
    let mut out = seed;
    for _ in 0..iters {
        out = pipe.run(black_box(seed)).unwrap();
    }
    let ns_total = t0.elapsed().as_nanos() as f64;
    let ns_per_iter = ns_total / iters as f64;
    let ns_per_hop = ns_per_iter / filters as f64;

    println!(
        "{{\"runtime\":\"rust\",\"variant\":\"typed\",\"filters\":{},\"iterations\":{},\"ns_per_iter\":{:.2},\"ns_per_hop\":{:.2},\"ops_per_sec\":{:.0},\"final_n\":{}}}",
        filters, iters, ns_per_iter, ns_per_hop, 1e9 / ns_per_iter, out.n
    );
}

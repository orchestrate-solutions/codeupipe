//! Native hop bench — matches cpp schema.
//! Usage: cargo run --release --example bench_hop -- [filters] [iters]

use codeupipe_core::{Filter, Payload, Pipeline};
use std::time::Instant;

struct Inc;
impl Filter for Inc {
    fn call(&self, p: Payload) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
        let n = p.get("n").and_then(|v| v.as_int()).unwrap_or(0);
        Ok(p.insert("n", (n + 1).into()))
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let filters: i64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(8);
    let iters: i64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(200_000);

    let mut pipe = Pipeline::new();
    for _ in 0..filters {
        pipe = pipe.add_filter(Inc);
    }
    pipe = pipe.observe_state(false);

    let seed = Payload::new().insert("n", 0_i64.into());
    for _ in 0..1000 {
        let _ = pipe.run(seed.clone());
    }

    let t0 = Instant::now();
    let mut out = seed.clone();
    for _ in 0..iters {
        out = pipe.run(seed.clone()).unwrap();
    }
    let ns_total = t0.elapsed().as_nanos() as f64;

    let ns_per_iter = ns_total / iters as f64;
    let ns_per_hop = ns_per_iter / filters as f64;
    let final_n = out.get("n").and_then(|v| v.as_int()).unwrap_or(0);
    println!(
        "{{\"runtime\":\"rust\",\"variant\":\"sync\",\"filters\":{},\"iterations\":{},\"ns_per_iter\":{:.2},\"ns_per_hop\":{:.2},\"ops_per_sec\":{:.0},\"final_n\":{}}}",
        filters, iters, ns_per_iter, ns_per_hop, 1e9 / ns_per_iter, final_n
    );
}

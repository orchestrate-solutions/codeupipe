//! The bench mode: times the scenarios as the Python runner does, so that
//! conformance/bench.py can put the numbers side by side.
use std::collections::HashMap;
use std::hint::black_box;
use std::time::{Duration, Instant};

use codeupipe::{Map, Pipeline, Value};

const WARMUP: usize = 20_000;
const RUNS: usize = 20_000;
const REPEATS: usize = 5;

const REFERENCE_KEYS: [&str; 10] = ["k0", "k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9"];

#[inline(never)]
fn reference_write(data: &mut HashMap<String, f64>, key: &str) {
    *data.entry(key.to_string()).or_insert(0.0) += 1.0;
}

/// The reference workload: ten map writes behind ten function calls, with no
/// framework. A pipeline's time is reported relative to it.
fn reference() -> HashMap<String, f64> {
    let mut data = HashMap::from([("a".to_string(), 1.0)]);
    for key in REFERENCE_KEYS {
        reference_write(&mut data, black_box(key));
    }
    data
}

fn timed(f: &mut impl FnMut()) -> Duration {
    let started = Instant::now();
    for _ in 0..RUNS {
        f();
    }
    started.elapsed()
}

/// (µs per run, time relative to the reference workload). µs per run is the
/// best of REPEATS x RUNS. Each repeat times the reference and then `f`,
/// back to back, and the median of the ratios is reported.
fn measure(mut f: impl FnMut()) -> (f64, f64) {
    let mut reference_run = || {
        black_box(reference());
    };
    for _ in 0..WARMUP {
        f();
        reference_run();
    }
    let mut best = Duration::MAX;
    let mut ratios = Vec::with_capacity(REPEATS);
    for _ in 0..REPEATS {
        let reference = timed(&mut reference_run);
        let elapsed = timed(&mut f);
        ratios.push(elapsed.as_secs_f64() / reference.as_secs_f64());
        best = best.min(elapsed);
    }
    ratios.sort_by(f64::total_cmp);
    let us_per_run = best.as_secs_f64() / RUNS as f64 * 1e6;
    (us_per_run, ratios[REPEATS / 2])
}

/// Time one scenario. `pipeline` is built from its steps; `input` is its input.
pub fn bench(id: Value, mut pipeline: Pipeline, input: codeupipe::Payload) -> Value {
    let output = match pipeline.run(&input) {
        Ok(output) => output.to_dict(),
        Err(error) => {
            return Value::Map(Map::from([
                ("id", id),
                (
                    "unsupported",
                    Value::from(format!("the scenario fails: {error}")),
                ),
            ]))
        }
    };
    let (us_per_run, relative) = measure(|| {
        black_box(pipeline.run(black_box(&input)).ok());
    });
    Value::Map(Map::from([
        ("id", id),
        ("us_per_run", Value::from(us_per_run)),
        ("relative", Value::from(relative)),
        ("output", Value::Map(output)),
    ]))
}

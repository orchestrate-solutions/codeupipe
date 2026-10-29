//! cargo run --release --example bench: each fixture pipeline against its
//! compiled module (tests/expected/), µs per run. The pipeline gets a Payload
//! and gives a Payload; the module gets its struct and gives its struct.
#[path = "../tests/fixtures/pricing/mod.rs"]
mod pricing;
#[path = "../tests/expected/pricing.rs"]
mod pricing_compiled;
#[path = "../tests/fixtures/signup/mod.rs"]
mod signup;
#[path = "../tests/expected/signup.rs"]
mod signup_compiled;

use std::hint::black_box;
use std::time::{Duration, Instant};

use codeupipe::{Payload, Pipeline};

const RUNS: u32 = 20_000;

// cup: allow-plain the timing loop of the bench: it measures the pipeline, so it is not a step of it
fn time(f: &mut impl FnMut()) -> Duration {
    let started = Instant::now();
    for _ in 0..RUNS {
        f();
    }
    started.elapsed()
}

/// The best of 9 rounds, the two alternated in each round so that the load of the machine falls on both.
// cup: allow-plain the timing loop of the bench: it measures the pipeline, so it is not a step of it
fn race(mut a: impl FnMut(), mut b: impl FnMut()) -> (f64, f64) {
    for _ in 0..3 {
        time(&mut a);
        time(&mut b);
    }
    let (mut best_a, mut best_b) = (Duration::MAX, Duration::MAX);
    for _ in 0..9 {
        best_a = best_a.min(time(&mut a));
        best_b = best_b.min(time(&mut b));
    }
    let us = |d: Duration| d.as_secs_f64() / f64::from(RUNS) * 1e6;
    (us(best_a), us(best_b))
}

fn main() {
    let pipeline = Pipeline::named(pricing::pricing_pipeline::PricingPipeline);
    let mut payload = Payload::new();
    payload.insert("price", 100.0).insert("qty", 12.0);
    let data = pricing_compiled::PricingData {
        price: Some(100.0),
        qty: Some(12.0),
        bulk: None,
    };
    let (dynamic, compiled) = race(
        || {
            black_box(pipeline.run(black_box(&payload)).ok());
        },
        || {
            black_box(pricing_compiled::run(black_box(&data)).ok());
        },
    );
    println!(
        "pricing (3 steps)  Pipeline::run {dynamic:.3} µs   compiled {compiled:.4} µs   {:.0}x",
        dynamic / compiled
    );

    let pipeline = Pipeline::named(signup::signup_pipeline::SignupPipeline);
    let mut payload = Payload::new();
    payload
        .insert("email", "  Ada@Example.COM ")
        .insert("coupon", "SAVE5");
    let data = signup_compiled::SignupData {
        email: Some("  Ada@Example.COM ".into()),
        coupon: Some("SAVE5".into()),
        ..Default::default()
    };
    let (dynamic, compiled) = race(
        || {
            black_box(pipeline.run(black_box(&payload)).ok());
        },
        || {
            black_box(signup_compiled::run(black_box(&data)).ok());
        },
    );
    println!("signup (4 steps, text)  Pipeline::run {dynamic:.3} µs   compiled {compiled:.4} µs   {:.1}x", dynamic / compiled);
}

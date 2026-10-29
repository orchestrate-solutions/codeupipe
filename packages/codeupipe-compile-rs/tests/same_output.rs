// The compiled modules in tests/expected/ give the output of the pipelines
// that they come from: the same keys and values, and the same error.
#[path = "fixtures/greet/mod.rs"]
mod greet;
#[path = "expected/greet.rs"]
mod greet_compiled;
#[path = "fixtures/pricing/mod.rs"]
mod pricing;
#[path = "expected/pricing.rs"]
mod pricing_compiled;
#[path = "fixtures/signup/mod.rs"]
mod signup;
#[path = "expected/signup.rs"]
mod signup_compiled;

use codeupipe::{Payload, Pipeline, Value};

fn text(payload: &Payload, key: &str) -> Option<String> {
    payload.get(key).and_then(Value::as_str).map(String::from)
}

#[test]
fn the_compiled_pricing_gives_the_output_of_the_pipeline() {
    let pipeline = Pipeline::named(pricing::pricing_pipeline::PricingPipeline);
    let inputs = [
        (Some(100.0), Some(12.0)),
        (Some(100.0), Some(3.0)),
        (Some(19.99), Some(10.0)),
        (Some(-5.0), Some(50.0)),
        (None, None),
        (Some(7.5), None),
    ];
    for (price, qty) in inputs {
        let mut payload = Payload::new();
        if let Some(price) = price {
            payload.insert("price", price);
        }
        if let Some(qty) = qty {
            payload.insert("qty", qty);
        }
        let data = pricing_compiled::PricingData {
            price,
            qty,
            bulk: None,
        };
        let dynamic = pipeline.run(&payload).map_err(|error| error.to_string());
        let compiled = pricing_compiled::run(&data).map_err(|error| error.to_string());
        let dynamic = dynamic.map(|out| pricing_compiled::PricingData {
            price: out.get("price").and_then(Value::as_f64),
            qty: out.get("qty").and_then(Value::as_f64),
            bulk: out.get("bulk").and_then(Value::as_bool),
        });
        assert_eq!(compiled, dynamic, "price {price:?}, qty {qty:?}");
    }
}

#[test]
fn the_compiled_signup_gives_the_output_of_the_pipeline_and_the_same_error() {
    let pipeline = Pipeline::named(signup::signup_pipeline::SignupPipeline);
    // The caller can give each key, also the ones that a step writes.
    let inputs = [
        (Some("  Ada@Example.COM "), Some("SAVE5"), None, None),
        (Some("bob@example.com"), None, None, None),
        (Some("bob@example.com"), None, Some("hi"), Some(2.0)),
        (Some("cy@example.com"), Some("SAVE5"), Some("hi"), Some(2.0)),
        (Some("   "), Some("X"), None, None),
        (None, None, None, None),
    ];
    for (email, coupon, message, discount) in inputs {
        let mut payload = Payload::new();
        if let Some(email) = email {
            payload.insert("email", email);
        }
        if let Some(coupon) = coupon {
            payload.insert("coupon", coupon);
        }
        if let Some(message) = message {
            payload.insert("message", message);
        }
        if let Some(discount) = discount {
            payload.insert("discount", discount);
        }
        let data = signup_compiled::SignupData {
            email: email.map(String::from),
            coupon: coupon.map(String::from),
            message: message.map(String::from),
            discount,
            ..Default::default()
        };
        let dynamic = pipeline.run(&payload).map_err(|error| error.to_string());
        let compiled = signup_compiled::run(&data).map_err(|error| error.to_string());
        let dynamic = dynamic.map(|out| signup_compiled::SignupData {
            email: text(&out, "email"),
            welcome: out.get("welcome").and_then(Value::as_bool),
            message: text(&out, "message"),
            coupon: text(&out, "coupon"),
            discount: out.get("discount").and_then(Value::as_f64),
        });
        assert_eq!(
            compiled, dynamic,
            "email {email:?}, coupon {coupon:?}, message {message:?}, discount {discount:?}"
        );
    }
}

#[test]
fn the_compiled_greet_gives_back_the_callers_text_that_no_step_writes() {
    let pipeline = Pipeline::named(greet::greet_pipeline::GreetPipeline);
    let inputs = [
        (Some("  Ada  "), Some("yes"), None),
        // The Valve writes over the caller's note.
        (Some("  Ada  "), Some("yes"), Some("an old note")),
        // The Valve does not run: the caller's note is given back.
        (Some("Bob"), None, Some("table 4")),
        (Some("Bob"), None, None),
        (None, None, None),
    ];
    for (name, vip, note) in inputs {
        let mut payload = Payload::new();
        for (key, value) in [("name", name), ("vip", vip), ("note", note)] {
            if let Some(value) = value {
                payload.insert(key, value);
            }
        }
        let data = greet_compiled::GreetData {
            name: name.map(String::from),
            vip: vip.map(String::from),
            note: note.map(String::from),
            badge: None,
        };
        let dynamic = pipeline.run(&payload).map_err(|error| error.to_string());
        let compiled = greet_compiled::run(&data).map_err(|error| error.to_string());
        let dynamic = dynamic.map(|out| greet_compiled::GreetData {
            name: text(&out, "name"),
            vip: text(&out, "vip"),
            note: text(&out, "note"),
            badge: text(&out, "badge"),
        });
        assert_eq!(
            compiled, dynamic,
            "name {name:?}, vip {vip:?}, note {note:?}"
        );
    }
}

#[test]
fn the_input_is_not_changed() {
    let data = pricing_compiled::PricingData {
        price: Some(100.0),
        qty: Some(12.0),
        bulk: None,
    };
    let before = data.clone();
    pricing_compiled::run(&data).unwrap();
    assert_eq!(data, before);
}

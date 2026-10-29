// A compiled run allocates only for the text that its steps make and for the
// caller's text that it gives back as it is. It does not copy text that a
// step writes over, and it makes a text setting once, not at each run.
#[path = "expected/greet.rs"]
mod greet_compiled;
#[path = "expected/signup.rs"]
mod signup_compiled;

use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;
use std::hint::black_box;

thread_local!(static ALLOCATIONS: Cell<u64> = const { Cell::new(0) });

/// The allocator of this test: the system's, with a count for each thread.
struct Counting;

unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        ALLOCATIONS.with(|count| count.set(count.get() + 1));
        System.alloc(layout)
    }

    unsafe fn dealloc(&self, at: *mut u8, layout: Layout) {
        System.dealloc(at, layout)
    }

    unsafe fn realloc(&self, at: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        ALLOCATIONS.with(|count| count.set(count.get() + 1));
        System.realloc(at, layout, size)
    }
}

#[global_allocator]
static ALLOCATOR: Counting = Counting;

/// How many times `f` allocates.
fn allocations(f: impl FnOnce()) -> u64 {
    let before = ALLOCATIONS.with(Cell::get);
    f();
    ALLOCATIONS.with(Cell::get) - before
}

#[test]
fn the_compiled_signup_allocates_only_the_text_that_its_steps_make() {
    let data = signup_compiled::SignupData {
        email: Some("  Ada@Example.COM ".into()),
        coupon: Some("SAVE5".into()),
        ..Default::default()
    };
    // The first run makes the setting.
    black_box(signup_compiled::run(&data).unwrap());
    let run = allocations(|| {
        black_box(signup_compiled::run(black_box(&data)).unwrap());
    });
    // The email made lower case, and the message. Not a copy of the email or
    // the coupon, and not the setting "Welcome".
    let welcome = String::from("Welcome");
    let made = allocations(|| {
        black_box(black_box("  Ada@Example.COM ").trim().to_lowercase());
        black_box(format!("{}!", black_box(&welcome)));
    });
    assert_eq!(run, made);
}

#[test]
fn the_compiled_greet_copies_only_the_callers_text_that_it_gives_back() {
    let data = greet_compiled::GreetData {
        name: Some("  Bob  ".into()),
        note: Some("table 4".into()),
        ..Default::default()
    };
    let run = allocations(|| {
        black_box(greet_compiled::run(black_box(&data)).unwrap());
    });
    // The trimmed name, and the caller's note, which the output gives back.
    // Not a copy of the name that the step writes over.
    let made = allocations(|| {
        black_box(black_box("  Bob  ").trim().to_string());
        black_box(black_box("table 4").to_string());
    });
    assert_eq!(run, made);
}

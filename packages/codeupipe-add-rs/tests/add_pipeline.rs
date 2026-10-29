// AddPipeline: the whole command on a project of its own, in a temporary
// directory. The five steps of the contract, in the order of the pipeline.
use std::fs;
use std::path::{Path, PathBuf};

use codeupipe_add::{add, AddRun, Refusal};

/// A new directory for one test, so that tests that run at the same time do
/// not see each other's files. It stays: the machine clears it.
fn project() -> PathBuf {
    let directory = std::env::temp_dir().join(format!(
        "cup-add-rs-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.subsec_nanos())
    ));
    fs::create_dir_all(directory.join("src")).expect("the project can be made");
    fs::write(
        directory.join("Cargo.toml"),
        "[package]\nname = \"the-project\"\nversion = \"0.1.0\"\n",
    )
    .expect("the manifest can be written");
    fs::write(directory.join("src/lib.rs"), "// the crate\n").expect("lib.rs can be written");
    directory
}

fn run(directory: &Path, kind: &str, name: &str) -> Result<AddRun, Refusal> {
    add(AddRun {
        root: directory.to_string_lossy().into_owned(),
        kind: kind.to_string(),
        name: name.to_string(),
        directory: "src".to_string(),
        ..AddRun::default()
    })
}

fn read(directory: &Path, path: &str) -> String {
    fs::read_to_string(directory.join(path)).unwrap_or_else(|error| panic!("{path}: {error}"))
}

#[test]
fn the_two_files_and_the_note_for_the_crate() {
    let directory = project();
    let run = run(&directory, "filter", "Discount").expect("the files are made");
    assert_eq!(
        run.written,
        ["src/discount_filter.rs", "tests/discount_filter.rs"]
    );
    assert_eq!(
        run.module_notes,
        ["add to src/lib.rs: pub mod discount_filter;"]
    );
    let component = read(&directory, "src/discount_filter.rs");
    assert!(
        component.contains("pub struct DiscountFilter;"),
        "{component}"
    );
    assert!(
        component.contains("TODO: say what DiscountFilter does."),
        "{component}"
    );
    let test = read(&directory, "tests/discount_filter.rs");
    assert!(
        test.contains("use the_project::discount_filter::DiscountFilter;"),
        "{test}"
    );
    assert!(
        test.contains("panic!(\"Write the acceptance case for DiscountFilter.\");"),
        "{test}"
    );
}

#[test]
fn the_description_goes_in_the_header() {
    let directory = project();
    let run = add(AddRun {
        root: directory.to_string_lossy().into_owned(),
        kind: "filter".to_string(),
        name: "Discount".to_string(),
        directory: "src".to_string(),
        description: "Takes a rate off the price.".to_string(),
        ..AddRun::default()
    })
    .expect("the files are made");
    let component = read(&directory, &run.written[0]);
    assert!(
        component.starts_with("//! DiscountFilter: Takes a rate off the price."),
        "{component}"
    );
}

#[test]
fn a_file_that_exists_stops_both_files() {
    let directory = project();
    fs::create_dir_all(directory.join("tests")).unwrap();
    fs::write(directory.join("tests/discount_filter.rs"), "existing\n").unwrap();
    let refusal = run(&directory, "filter", "Discount").expect_err("a file exists");
    assert_eq!(refusal.exit_code, 1);
    assert_eq!(refusal.message, "tests/discount_filter.rs exists");
    assert!(
        !directory.join("src/discount_filter.rs").exists(),
        "the component was written all the same"
    );
    assert_eq!(
        read(&directory, "tests/discount_filter.rs"),
        "existing\n",
        "the file that was there changed"
    );
}

#[test]
fn a_component_in_a_directory_needs_two_notes_and_no_third_file() {
    let directory = project();
    let run = add(AddRun {
        root: directory.to_string_lossy().into_owned(),
        kind: "filter".to_string(),
        name: "Discount".to_string(),
        directory: "src/pricing".to_string(),
        ..AddRun::default()
    })
    .expect("the files are made");
    assert_eq!(
        run.written,
        ["src/pricing/discount_filter.rs", "tests/discount_filter.rs"]
    );
    assert_eq!(
        run.module_notes,
        [
            "add to src/lib.rs: pub mod pricing;",
            "add to src/pricing.rs: pub mod discount_filter;"
        ]
    );
    // The two files of the contract, and nothing else.
    assert!(directory.join("src/pricing/discount_filter.rs").is_file());
    assert!(!directory.join("src/pricing.rs").exists());
    assert!(!directory.join("src/pricing/mod.rs").exists());
    assert!(read(&directory, "tests/discount_filter.rs")
        .contains("use the_project::pricing::discount_filter::DiscountFilter;"));
}

#[test]
fn a_note_is_left_out_when_the_crate_has_the_line_already() {
    let directory = project();
    fs::write(directory.join("src/lib.rs"), "pub mod pricing;\n").unwrap();
    let run = add(AddRun {
        root: directory.to_string_lossy().into_owned(),
        kind: "filter".to_string(),
        name: "Discount".to_string(),
        directory: "src/pricing".to_string(),
        ..AddRun::default()
    })
    .expect("the files are made");
    assert_eq!(
        run.module_notes,
        ["add to src/pricing.rs: pub mod discount_filter;"]
    );
}

#[test]
fn a_directory_that_goes_out_of_the_project_is_refused() {
    let directory = project();
    let refusal = add(AddRun {
        root: directory.to_string_lossy().into_owned(),
        kind: "filter".to_string(),
        name: "Discount".to_string(),
        directory: "../outside".to_string(),
        ..AddRun::default()
    })
    .expect_err("the directory cannot be used");
    assert_eq!(refusal.exit_code, 2);
    assert!(
        refusal.message.contains("../outside"),
        "{}",
        refusal.message
    );
    assert!(!directory.join("src/discount_filter.rs").exists());
}

#[test]
fn each_kind_returns_the_data_unchanged_or_does_nothing() {
    use codeupipe::{Filter, Hook, NamedPipeline, Payload, Pipeline, Predicate, Tap};
    let directory = project();
    for kind in ["filter", "predicate", "tap", "hook", "pipeline"] {
        let run = run(&directory, kind, "Sample").expect("the files are made");
        let component = read(&directory, &run.written[0]);
        assert!(component.contains(&run.type_name), "{kind}: {component}");
        fs::remove_file(directory.join(&run.written[0])).unwrap();
        fs::remove_file(directory.join(&run.written[1])).unwrap();
    }
    // The five texts are Rust: each declares its type and implements its role.
    let mut pipeline = Pipeline::new();
    struct NoFilter;
    impl Filter for NoFilter {
        fn call(&self, payload: &mut Payload) -> Result<(), codeupipe::StepError> {
            let _ = payload;
            Ok(())
        }
    }
    struct NoPredicate;
    impl Predicate for NoPredicate {
        fn test(&self, payload: &Payload) -> bool {
            let _ = payload;
            false
        }
    }
    struct NoTap;
    impl Tap for NoTap {
        fn observe(&self, payload: &Payload) -> Result<(), codeupipe::StepError> {
            let _ = payload;
            Ok(())
        }
    }
    struct NoHook;
    impl Hook for NoHook {}
    struct NoPipeline;
    impl NamedPipeline for NoPipeline {
        fn add_steps(&self, _pipeline: &mut Pipeline) {}
    }
    pipeline.add_filter(NoFilter);
    pipeline.add_valve(NoPredicate, NoFilter);
    pipeline.add_tap(NoTap);
    pipeline.add_pipeline(Pipeline::named(NoPipeline));
    pipeline.use_hook(NoHook);
    let out = pipeline.run(&Payload::new()).expect("the run goes through");
    assert!(!out.has("anything"));
}

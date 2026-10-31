// LayoutPipeline: `codeupipe add --layout` on a project of its own, in a
// temporary directory (conformance/ADD.md, "Phase 2: a layout").
use std::fs;
use std::path::{Path, PathBuf};

use codeupipe_add::{layout, LayoutRun, Refusal};

const PRICING: &str = "lang: rust
root: src/pricing
components:
  - {kind: filter, name: Discount, description: \"Takes a rate off the price.\"}
  - {kind: predicate, name: AtLeast}
  - {kind: filter, name: MarkBulk}
  - {kind: hook, name: PrintSteps}
  - {kind: pipeline, name: Clean, steps: [Discount]}
  - kind: pipeline
    name: Pricing
    steps: [CleanPipeline, {valve: [AtLeast, MarkBulk]}]
    hooks: [PrintSteps]
";

/// A new project for one test, with the layout in `cup.layout.yaml`.
fn project(layout_text: &str) -> PathBuf {
    let directory = std::env::temp_dir().join(format!(
        "cup-add-layout-rs-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.as_nanos())
    ));
    fs::create_dir_all(directory.join("src")).expect("the project can be made");
    fs::write(
        directory.join("Cargo.toml"),
        "[package]\nname = \"the-project\"\n",
    )
    .expect("the manifest");
    fs::write(directory.join("src/lib.rs"), "// the crate\n").expect("lib.rs");
    fs::write(directory.join("cup.layout.yaml"), layout_text).expect("the layout");
    directory
}

fn run(directory: &Path) -> Result<LayoutRun, Refusal> {
    layout(LayoutRun {
        root: directory.to_string_lossy().into_owned(),
        layout_path: "cup.layout.yaml".to_string(),
        ..LayoutRun::default()
    })
}

fn refused(layout_text: &str) -> String {
    let directory = project(layout_text);
    let refusal = run(&directory).expect_err("the layout is refused");
    assert_eq!(refusal.exit_code, 2, "{}", refusal.message);
    assert!(
        !directory.join("src/pricing").exists(),
        "nothing is written"
    );
    refusal.message
}

#[test]
fn each_component_its_steps_and_the_notes_for_the_crate() {
    let directory = project(PRICING);
    let done = run(&directory).expect("the files are made");
    assert_eq!(done.written.len(), 12);
    assert_eq!(done.written[0], "src/pricing/discount_filter.rs");
    assert_eq!(done.written[1], "tests/discount_filter.rs");
    assert_eq!(done.module_notes[0], "add to src/lib.rs: pub mod pricing;");
    assert_eq!(
        done.module_notes[1],
        "add to src/pricing.rs: pub mod discount_filter;"
    );
    assert_eq!(done.module_notes.len(), 7, "{:?}", done.module_notes);
    let pricing = fs::read_to_string(directory.join("src/pricing/pricing_pipeline.rs"))
        .expect("the pipeline");
    for line in [
        "use crate::pricing::at_least_predicate::AtLeastPredicate;",
        "use crate::pricing::clean_pipeline::CleanPipeline;",
        "        pipeline.add_pipeline(Pipeline::named(CleanPipeline));",
        "        pipeline.add_valve(AtLeastPredicate, MarkBulkFilter);",
        "        pipeline.use_hook(PrintStepsHook);",
    ] {
        assert!(pricing.contains(line), "{line}\n{pricing}");
    }
}

#[test]
fn a_second_run_keeps_each_file_and_names_a_pipeline_whose_steps_changed() {
    let directory = project(PRICING);
    run(&directory).expect("the first run");
    let again = run(&directory).expect("the second run");
    assert!(again.written.is_empty());
    assert_eq!(again.kept.len(), 12);
    assert!(again.stale.is_empty(), "{:?}", again.stale);
    fs::write(
        directory.join("cup.layout.yaml"),
        PRICING.replace("steps: [Discount]", "steps: [Discount, MarkBulk]"),
    )
    .expect("the grown layout");
    let grown = run(&directory).expect("the third run");
    assert_eq!(grown.stale, ["src/pricing/clean_pipeline.rs"]);
}

#[test]
fn json_is_read_as_yaml() {
    let directory = project("");
    fs::write(
        directory.join("cup.layout.yaml"),
        r#"{"lang": "rust", "root": "src", "components": [{"kind": "tap", "name": "Audit"}]}"#,
    )
    .expect("the layout");
    assert_eq!(
        run(&directory).expect("the files").written,
        ["src/audit_tap.rs", "tests/audit_tap.rs"]
    );
}

#[test]
fn each_rule_of_the_contract_refuses_the_whole_layout() {
    let base = "lang: rust\nroot: src/pricing\ncomponents:\n";
    let discount = "  - {kind: filter, name: Discount}\n";
    for (text, wanted) in [
        ("- lang: rust\n".to_string(), "is not a mapping"),
        (format!("{base}  - kind: filter\n    name: A\n    name: B\n"), "has the key name two times"),
        (format!("lang: go\ncomponents:\n{discount}"), "is for go, and this is codeupipe add for rust"),
        (format!("components:\n{discount}"), "has no lang:"),
        (format!("{base}  - {{kind: filter, name: Discount, step: []}}\n"), "Unknown key step"),
        (format!("{base}  - {{kind: filter, name: Discount, steps: []}}\n"), "steps: is only for a pipeline"),
        (format!("{base}{discount}  - {{kind: filter, name: DiscountFilter}}\n"), "Two components are DiscountFilter"),
        (format!("{base}  - {{kind: pipeline, name: P, steps: [Tax]}}\n"), "Tax, a step of P, is not a component"),
        (
            format!("{base}  - {{kind: pipeline, name: Outer, steps: [Inner]}}\n  - {{kind: pipeline, name: Inner, steps: [Outer]}}\n"),
            "OuterPipeline -> InnerPipeline -> OuterPipeline",
        ),
        (
            format!("{base}{discount}  - {{kind: predicate, name: AtLeast}}\n  - {{kind: pipeline, name: P, steps: [{{valve: [Discount, AtLeast]}}]}}\n"),
            "a valve is [Predicate, Filter], and Discount is a filter",
        ),
        (format!("{base}  - {{kind: valve, name: Bulk}}\n"), "add_valve(predicate, filter)"),
    ] {
        let message = refused(&text);
        assert!(message.contains(wanted), "{wanted}: {message}");
    }
}

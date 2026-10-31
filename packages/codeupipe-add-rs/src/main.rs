//! codeupipe add <kind> <name> [dir] [--description TEXT]
//! codeupipe add --layout cup.layout.yaml
//!
//! Makes the component file and the test file of one component, in the
//! directory where the command runs, which is the root of the project
//! (conformance/ADD.md). Prints each file that it made, one path in each
//! line, the component first. The lines that the crate needs for the new file
//! to be a module go to stderr, because a new file in `src` is a module only
//! when the crate says so, and the command edits no file that is there
//! already.
//!
//! Exit code: 0 the files are made, 1 a file exists (nothing is written),
//! 2 the arguments cannot be used (nothing is written). With --layout, a file
//! that exists is kept, and the exit code is 0.

use std::env;
use std::process::ExitCode;

use codeupipe_add::{add, layout, AddRun, LayoutRun, Refusal};

const USAGE: &str =
    "Usage: codeupipe add <kind> <name> [dir] [--description TEXT]\n       codeupipe add --layout FILE";

/// What one run of the command did: one component, or a layout.
enum Done {
    One(AddRun),
    Layout(LayoutRun),
}

// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
fn main() -> ExitCode {
    match run(env::args().skip(1).collect()) {
        Ok(Done::One(run)) => {
            for path in run.written {
                println!("{path}");
            }
            for note in run.module_notes {
                eprintln!("{note}");
            }
            ExitCode::SUCCESS
        }
        Ok(Done::Layout(run)) => {
            for path in &run.kept {
                if run.stale.contains(path) {
                    eprintln!(
                        "{path} exists, kept, and its steps are not those of the layout. Change the file: the command does not write it again."
                    );
                } else {
                    eprintln!("{path} exists, kept");
                }
            }
            for path in run.written {
                println!("{path}");
            }
            for note in run.module_notes {
                eprintln!("{note}");
            }
            ExitCode::SUCCESS
        }
        Err(refusal) => {
            eprintln!("{}", refusal.message);
            ExitCode::from(refusal.exit_code)
        }
    }
}

/// The arguments of the command, then one run of the pipeline.
// cup: allow-plain the entry of the program: it reads the arguments and writes nothing itself
fn run(argv: Vec<String>) -> Result<Done, Refusal> {
    let mut args: Vec<String> = Vec::new();
    let mut description: Option<String> = None;
    let mut layout_path: Option<String> = None;
    let mut argv = argv.into_iter();
    while let Some(arg) = argv.next() {
        if let Some((name, inline)) = arg.split_once('=') {
            if name == "--description" {
                description = Some(inline.to_string());
                continue;
            }
            if name == "--layout" {
                layout_path = Some(inline.to_string());
                continue;
            }
        }
        if arg == "--description" || arg == "--layout" {
            let value = argv
                .next()
                .ok_or_else(|| Refusal::usage(format!("option '{arg}' needs a value.\n{USAGE}")))?;
            if arg == "--layout" {
                layout_path = Some(value);
            } else {
                description = Some(value);
            }
            continue;
        }
        if arg.starts_with("--") {
            return Err(Refusal::usage(format!("unknown option '{arg}'.\n{USAGE}")));
        }
        args.push(arg);
    }
    let root = env::current_dir()
        .map(|root| root.to_string_lossy().into_owned())
        .unwrap_or_else(|_| ".".to_string());
    if let Some(layout_path) = layout_path {
        if !args.is_empty() || description.is_some() {
            return Err(Refusal::usage(
                "--layout takes no kind, name, dir or --description: they are in the layout.",
            ));
        }
        return layout(LayoutRun {
            root,
            layout_path,
            ..LayoutRun::default()
        })
        .map(Done::Layout);
    }
    if args.is_empty() {
        return Err(Refusal::usage(format!(
            "give the kind of the component: filter, predicate, tap, hook or pipeline.\n{USAGE}"
        )));
    }
    if args.len() < 2 {
        return Err(Refusal::usage(format!(
            "give the name of the component, as well as its kind.\n{USAGE}"
        )));
    }
    if args.len() > 3 {
        return Err(Refusal::usage(format!("too many arguments.\n{USAGE}")));
    }
    add(AddRun {
        root,
        kind: args[0].clone(),
        name: args[1].clone(),
        directory: args.get(2).cloned().unwrap_or_else(|| "src".to_string()),
        description: description.unwrap_or_default(),
        ..AddRun::default()
    })
    .map(Done::One)
}

//! codeupipe add <kind> <name> [dir] [--description TEXT]
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
//! 2 the arguments cannot be used (nothing is written).

use std::env;
use std::process::ExitCode;

use codeupipe_add::{add, AddRun, Refusal};

const USAGE: &str = "Usage: codeupipe add <kind> <name> [dir] [--description TEXT]";

// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
fn main() -> ExitCode {
    match run(env::args().skip(1).collect()) {
        Ok(run) => {
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
fn run(argv: Vec<String>) -> Result<AddRun, Refusal> {
    let mut args: Vec<String> = Vec::new();
    let mut description = String::new();
    let mut argv = argv.into_iter();
    while let Some(arg) = argv.next() {
        if let Some((name, inline)) = arg.split_once('=') {
            if name == "--description" {
                description = inline.to_string();
                continue;
            }
        }
        if arg == "--description" {
            description = argv.next().ok_or_else(|| {
                Refusal::usage(format!("option '--description' needs a value.\n{USAGE}"))
            })?;
            continue;
        }
        if arg.starts_with("--") {
            return Err(Refusal::usage(format!("unknown option '{arg}'.\n{USAGE}")));
        }
        args.push(arg);
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
        root: env::current_dir()
            .map(|root| root.to_string_lossy().into_owned())
            .unwrap_or_else(|_| ".".to_string()),
        kind: args[0].clone(),
        name: args[1].clone(),
        directory: args.get(2).cloned().unwrap_or_else(|| "src".to_string()),
        description,
        ..AddRun::default()
    })
}

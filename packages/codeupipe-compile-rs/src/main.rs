//! codeupipe-compile PATH... PIPELINE [--out FILE]
//!
//! Writes the pipeline PIPELINE (the name of its type) from the Rust files
//! under the paths as plain Rust, to FILE or to stdout. Exit code: 0 the
//! module is written, 1 the pipeline is refused (the message names the place
//! and the fix), 2 the command could not run. Nothing is written on 1 or 2.
use std::process::ExitCode;

use codeupipe_compile::compile;

// cup: allow-plain the entry of the program: it reads the arguments and writes the module
fn main() -> ExitCode {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let out = match args.iter().position(|arg| arg == "--out") {
        Some(at) if at + 1 < args.len() => {
            let file = args.remove(at + 1);
            args.remove(at);
            Some(file)
        }
        Some(_) => return usage(),
        None => None,
    };
    let Some(pipeline) = args.pop() else {
        return usage();
    };
    if args.is_empty() {
        return usage();
    }
    match compile(&args, &pipeline) {
        Ok(module) => match out {
            Some(file) => match std::fs::write(&file, module) {
                Ok(()) => ExitCode::SUCCESS,
                Err(error) => {
                    eprintln!("{file}: {error}");
                    ExitCode::from(2)
                }
            },
            None => {
                print!("{module}");
                ExitCode::SUCCESS
            }
        },
        Err(refusal) => {
            eprintln!("{refusal}");
            ExitCode::from(1)
        }
    }
}

fn usage() -> ExitCode {
    eprintln!("Usage: codeupipe-compile PATH... PIPELINE [--out FILE]");
    ExitCode::from(2)
}

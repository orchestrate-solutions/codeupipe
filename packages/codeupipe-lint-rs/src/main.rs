//! codeupipe-lint [--exclude GLOB] [--disable RULE] [--strict] [--config FILE] [--rules] [paths...]
//!
//! With no paths, they come from cup.config.json. Exit code: 0 no findings,
//! 1 findings, 2 a path could not be read or the arguments cannot be used.
//! A warning does not make the exit code 1, unless --strict is given.

use std::process::ExitCode;

use codeupipe_lint::{lint_paths, read_lint_config, LintOptions, CONFIG_NAME, RULES};

/// The arguments of the command.
#[derive(Default)]
struct Args {
    paths: Vec<String>,
    exclude: Option<Vec<String>>,
    disable: Option<Vec<String>>,
    config: Option<String>,
    rules: bool,
    strict: bool,
}

// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
fn main() -> ExitCode {
    match run(std::env::args().skip(1).collect()) {
        Ok(code) => ExitCode::from(code),
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::from(2)
        }
    }
}

// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
fn run(argv: Vec<String>) -> Result<u8, String> {
    let mut args = parse(argv)?;
    if args.rules {
        for rule in RULES {
            println!("{}  {}", rule.id, rule.slug);
        }
        return Ok(0);
    }
    if args.paths.is_empty() {
        // The file stands in for the arguments only when no paths are given:
        // a path that someone names is checked, whatever the file excludes.
        let lint = read_lint_config(args.config.as_deref())?.unwrap_or_default();
        args.paths = lint.paths.unwrap_or_default();
        args.exclude = args.exclude.or(lint.exclude);
        args.disable = args.disable.or(lint.disable);
    }
    if args.paths.is_empty() {
        return Err(format!(
            "give at least one path, or list them under lint.paths in {CONFIG_NAME}"
        ));
    }
    let disable = args.disable.unwrap_or_default();
    let unknown: Vec<&str> = disable
        .iter()
        .filter(|id| !RULES.iter().any(|rule| rule.id == id.as_str()))
        .map(String::as_str)
        .collect();
    if !unknown.is_empty() {
        return Err(format!(
            "no such rule: {} (the rules are listed by --rules)",
            unknown.join(", ")
        ));
    }
    let options = LintOptions {
        exclude: args.exclude.unwrap_or_default(),
        disable,
        strict: args.strict,
    };
    let out = lint_paths(&args.paths, &options).map_err(|error| error.to_string())?;
    println!("{}", out.report);
    if !out.error_report.is_empty() {
        eprintln!("{}", out.error_report);
    }
    Ok(out.exit_code as u8)
}

// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
fn parse(argv: Vec<String>) -> Result<Args, String> {
    let mut args = Args::default();
    let mut argv = argv.into_iter();
    while let Some(arg) = argv.next() {
        let (name, inline) = match arg.split_once('=') {
            Some((name, value)) if name.starts_with("--") => {
                (name.to_string(), Some(value.to_string()))
            }
            _ => (arg.clone(), None),
        };
        let mut value = || {
            inline
                .clone()
                .or_else(|| argv.next())
                .ok_or_else(|| format!("option '{name}' needs a value"))
        };
        match name.as_str() {
            "--exclude" => args.exclude.get_or_insert_with(Vec::new).push(value()?),
            "--disable" => args.disable.get_or_insert_with(Vec::new).push(value()?),
            "--config" => args.config = Some(value()?),
            "--rules" => args.rules = true,
            "--strict" => args.strict = true,
            _ if name.starts_with("--") => return Err(format!("unknown option '{name}'")),
            _ => args.paths.push(arg),
        }
    }
    Ok(args)
}

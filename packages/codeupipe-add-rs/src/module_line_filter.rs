use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::templates;

/// The note about modules that the command writes on stderr.
///
/// A new file in `src` is a module only when the crate says so, and the
/// command does not edit a file that is there already (conformance/ADD.md,
/// "Rust and Go: the package"), so it writes one line for each line that is
/// needed, in the order in which they are needed. A user, or the judge, adds
/// each line to the file that its name gives, and makes a file that is not
/// there yet.
///
/// A component in `src` needs one: `add to src/lib.rs: pub mod
/// discount_filter;`. A component in a directory of its own (`src/pricing`)
/// needs two: the crate names the directory, and the file of that directory
/// names the component. Neither file is one of the two of the contract, so
/// the command makes neither of them. A line that the file has already is
/// left out, so a second component of the same directory does not ask for the
/// same module again.
///
/// Reads `directory_module_path` (DirectoryModuleFilter), `snake`, and the
/// files that the project has. Writes `module_notes`: each note, as the
/// command prints it, in order.
pub struct ModuleLineFilter;

impl Filter<AddRun> for ModuleLineFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let component = templates::MODULE_LINE.replace("{snake}", &run.snake);
        if run.directory_module_path.is_empty() {
            run.module_notes = kept(run, "src/lib.rs", &component);
            return Ok(());
        }
        let name = run
            .directory_module_path
            .strip_suffix(".rs")
            .and_then(|path| path.rsplit('/').next())
            .unwrap_or(&run.directory_module_path);
        let directory = templates::MODULE_LINE.replace("{snake}", name);
        let mut notes = kept(run, "src/lib.rs", &directory);
        notes.extend(kept(run, &run.directory_module_path, &component));
        run.module_notes = notes;
        Ok(())
    }
}

/// The one note that asks for `line` in `file`, with nothing when the file
/// has that line already.
// cup: allow-plain the reading of one line of a file: it is a check of text, not a step
fn kept(run: &AddRun, file: &str, line: &str) -> Vec<String> {
    if has_line(run, file, line) {
        return Vec::new();
    }
    vec![format!("add to {file}: {line}")]
}

/// The text of `file` in the project, or nothing when it is not there.
// cup: allow-plain the reading of a file of the project: it is an input of the step, not a step
fn text_of(run: &AddRun, file: &str) -> String {
    let path = std::path::Path::new(&run.root).join(file);
    std::fs::read_to_string(path).unwrap_or_default()
}

/// A file of the project that has `line` at its start, with no space before
/// it. A comment or a `mod` in a function does not count.
// cup: allow-plain a check of the text of a file: it is a rule of the step, not a step
fn has_line(run: &AddRun, file: &str, line: &str) -> bool {
    text_of(run, file)
        .lines()
        .any(|text| text.trim_end() == line)
}

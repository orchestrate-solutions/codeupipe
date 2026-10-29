use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::compile_run::CompileRun;
use crate::place::Place;
use crate::refusal::Refusal;
use crate::source::Source;

/// Reads and parses each Rust file under the paths, in the order of their names.
pub struct ReadSourcesFilter;

impl ReadSourcesFilter {
    fn files(path: &Path, into: &mut Vec<String>) -> Result<(), StepError> {
        if path.is_dir() {
            let mut entries: Vec<_> = fs::read_dir(path)?
                .filter_map(Result::ok)
                .map(|entry| entry.path())
                .collect();
            entries.sort();
            for entry in entries {
                Self::files(&entry, into)?;
            }
        } else if path.extension().is_some_and(|ext| ext == "rs") {
            into.push(path.to_string_lossy().into_owned());
        }
        Ok(())
    }
}

impl Filter<CompileRun> for ReadSourcesFilter {
    fn call(&self, run: &mut CompileRun) -> Result<(), StepError> {
        let mut files = Vec::new();
        for path in &run.paths {
            if !Path::new(path).exists() {
                return Err(Refusal::new(
                    Place {
                        path: path.clone(),
                        line: 0,
                        col: 0,
                    },
                    "There is no such file or directory",
                    "Give the files of the pipeline and its steps",
                )
                .into());
            }
            Self::files(Path::new(path), &mut files)?;
        }
        for path in files {
            let text = fs::read_to_string(&path)?;
            let tree = syn::parse_file(&text).map_err(|error| {
                Refusal::new(
                    Place::of(&path, error.span()),
                    format!("The file does not parse: {error}"),
                    "Fix the syntax",
                )
            })?;
            run.sources.push(Source { path, tree });
        }
        Ok(())
    }
}

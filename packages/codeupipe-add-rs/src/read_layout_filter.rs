use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::layout_run::LayoutRun;
use crate::layout_value::LayoutValue;
use crate::refusal::Refusal;

/// The layout file, as data (conformance/ADD.md, "The YAML reader").
///
/// Reads `root` and `layout_path`. Writes `layout`. Rust has no YAML or JSON
/// reader in its standard library, so the `layout` feature (on by default)
/// reads both with yaml-rust2: JSON is YAML. A file that cannot be read, a key
/// two times in one mapping, or a layout that is not a mapping is refused
/// with exit code 2.
pub struct ReadLayoutFilter;

impl Filter<LayoutRun> for ReadLayoutFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        let path = run.layout_path.clone();
        let text = fs::read_to_string(Path::new(&run.root).join(&path)).map_err(|error| {
            Refusal::usage(format!("The layout {path} cannot be read: {error}"))
        })?;
        let layout = read(&path, &text)?;
        if !matches!(layout, LayoutValue::Map(_)) {
            return Err(Refusal::usage(format!(
                "The layout {path} is not a mapping. It starts with keys such as lang: and components:."
            ))
            .into());
        }
        run.layout = Some(layout);
        Ok(())
    }
}

/// The first document of the file. A key two times in one mapping is an
/// error of the reader, which names the key and the line.
#[cfg(feature = "layout")]
// cup: allow-plain the call of the YAML reader, which is the dependency of the feature
fn read(path: &str, text: &str) -> Result<LayoutValue, Refusal> {
    let documents = yaml_rust2::YamlLoader::load_from_str(text).map_err(|error| {
        let info = error.info();
        match info.strip_suffix(": duplicated key in mapping") {
            Some(key) => Refusal::usage(format!(
                "The layout {path}, line {} has the key {} two times in one mapping. Keep one.",
                error.marker().line(),
                key.strip_prefix("String(\"")
                    .and_then(|key| key.strip_suffix("\")"))
                    .unwrap_or(key)
            )),
            None => Refusal::usage(format!("The layout {path} cannot be read: {error}")),
        }
    })?;
    Ok(documents
        .first()
        .map_or(LayoutValue::Other("null".to_string()), value_of))
}

/// Without the `layout` feature, the command makes one component, and a
/// layout is refused with the way to get the feature.
#[cfg(not(feature = "layout"))]
fn read(path: &str, _text: &str) -> Result<LayoutValue, Refusal> {
    Err(Refusal::usage(format!(
        "The layout {path} needs the layout feature of codeupipe-add, which reads YAML: build it with --features layout."
    )))
}

/// The value of the reader as a LayoutValue, in the order of the file.
#[cfg(feature = "layout")]
// cup: allow-plain the data of the YAML reader as a LayoutValue: a conversion, not a step
fn value_of(yaml: &yaml_rust2::Yaml) -> LayoutValue {
    use yaml_rust2::Yaml;
    match yaml {
        Yaml::Hash(pairs) => LayoutValue::Map(
            pairs
                .iter()
                .map(|(key, value)| (key_of(key), value_of(value)))
                .collect(),
        ),
        Yaml::Array(items) => LayoutValue::List(items.iter().map(value_of).collect()),
        Yaml::String(text) => LayoutValue::Text(text.clone()),
        other => LayoutValue::Other(key_of(other)),
    }
}

/// A key as a text: a key that is not a text is shown as the reader has it.
#[cfg(feature = "layout")]
// cup: allow-plain the text of one key of the YAML reader: a conversion, not a step
fn key_of(yaml: &yaml_rust2::Yaml) -> String {
    use yaml_rust2::Yaml;
    match yaml {
        Yaml::String(text) | Yaml::Real(text) => text.clone(),
        Yaml::Integer(number) => number.to_string(),
        Yaml::Boolean(value) => value.to_string(),
        Yaml::Null => "null".to_string(),
        _ => "?".to_string(),
    }
}

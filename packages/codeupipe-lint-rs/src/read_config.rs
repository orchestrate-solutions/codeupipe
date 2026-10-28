use std::fs;
use std::path::Path;

use serde_json::Value;

/// The file that holds the settings of the project's tools.
pub const CONFIG_NAME: &str = "cup.config.json";
const LINT_KEYS: &[&str] = &["paths", "exclude", "disable"];

/// The `lint` section of the config file.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct LintConfig {
    pub paths: Option<Vec<String>>,
    pub exclude: Option<Vec<String>>,
    pub disable: Option<Vec<String>>,
}

/// The `lint` section of the config file, checked. `None` when the file is
/// not there. With `path` given, a file that is not there is an error.
///
/// A key that the linter does not read is an error, so the file cannot hold
/// a setting that does nothing. Other sections of the file are for other
/// tools.
// cup: allow-plain the edge of the program: it reads the config file before the pipeline runs
pub fn read_lint_config(path: Option<&str>) -> Result<Option<LintConfig>, String> {
    let name = path.unwrap_or(CONFIG_NAME);
    if !Path::new(name).exists() {
        return match path {
            None => Ok(None),
            Some(_) => Err(format!("{name}: no such file")),
        };
    }
    let text = fs::read_to_string(name).map_err(|error| format!("{name}: {error}"))?;
    let config: Value = serde_json::from_str(&text)
        .map_err(|error| format!("{name} is not valid JSON: {error}"))?;
    let Value::Object(config) = config else {
        return Err(format!("{name} must hold a JSON object"));
    };
    let lint = match config.get("lint") {
        None => return Ok(Some(LintConfig::default())),
        Some(Value::Object(lint)) => lint,
        Some(_) => return Err(format!("{name}: lint must be an object")),
    };
    let mut out = LintConfig::default();
    for (key, value) in lint {
        let strings: Option<Vec<String>> = value.as_array().and_then(|items| {
            items
                .iter()
                .map(|item| item.as_str().map(String::from))
                .collect()
        });
        let slot = match key.as_str() {
            "paths" => &mut out.paths,
            "exclude" => &mut out.exclude,
            "disable" => &mut out.disable,
            _ => {
                return Err(format!(
                    "{name}: lint: unknown key '{key}' (the keys are {})",
                    LINT_KEYS.join(", ")
                ))
            }
        };
        *slot =
            Some(strings.ok_or_else(|| format!("{name}: lint.{key} must be a list of strings"))?);
    }
    Ok(Some(out))
}

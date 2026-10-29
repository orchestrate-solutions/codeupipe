use codeupipe::{Filter, StepError};

use crate::compile_run::CompileRun;
use crate::key_type::KeyType;
use crate::payload_rewriter::PayloadRewriter;
use crate::refusal::Refusal;

/// Gives each key one type, from the reads and the writes that show one, in
/// the order of its first use. A key that two uses give two types is
/// refused. A key that is only tested (`has`) or removed is text. A key that
/// a step writes with a value whose type the code does not show, and that
/// no use gives a type, is refused.
pub struct TypeKeysFilter;

impl Filter<CompileRun> for TypeKeysFilter {
    fn call(&self, run: &mut CompileRun) -> Result<(), StepError> {
        let mut keys: Vec<(String, String, Option<KeyType>, Option<usize>)> = Vec::new();
        for (at, key_use) in run.uses.iter().enumerate() {
            let known = keys.iter().position(|(key, ..)| *key == key_use.key);
            let index = match known {
                Some(index) => index,
                None => {
                    keys.push((
                        key_use.key.clone(),
                        PayloadRewriter::field_of(&key_use.key),
                        None,
                        None,
                    ));
                    keys.len() - 1
                }
            };
            let entry = &mut keys[index];
            if key_use.untyped_write && entry.3.is_none() {
                entry.3 = Some(at);
            }
            let Some(key_type) = key_use.key_type else {
                continue;
            };
            match entry.2 {
                None => entry.2 = Some(key_type),
                Some(before) if before != key_type => {
                    let first = run
                        .uses
                        .iter()
                        .find(|u| u.key == key_use.key && u.key_type == Some(before))
                        .expect("the use that gave the first type");
                    let what = format!(
                        "The key \"{}\" is {} in {} and {} in {}",
                        key_use.key,
                        before.name(),
                        first.step,
                        key_type.name(),
                        key_use.step
                    );
                    return Err(Refusal::new(
                        key_use.place.clone(),
                        what,
                        "Give each key one type",
                    )
                    .into());
                }
                Some(_) => {}
            }
        }
        for (key, field, key_type, untyped) in &keys {
            if key_type.is_none() {
                if let Some(at) = untyped {
                    let key_use = &run.uses[*at];
                    let what = format!("The type of the key \"{key}\" cannot be told");
                    return Err(Refusal::new(
                        key_use.place.clone(),
                        what,
                        "Read the key once with .and_then(Value::as_...), or write a literal",
                    )
                    .into());
                }
            }
            if let Some(other) = keys
                .iter()
                .find(|(other, other_field, ..)| other != key && other_field == field)
            {
                let what = format!(
                    "The keys \"{key}\" and \"{}\" give the same field `{field}`",
                    other.0
                );
                return Err(Refusal::new(
                    run.uses[0].place.clone(),
                    what,
                    "Give the keys names that differ in letters, digits or _",
                )
                .into());
            }
        }
        run.keys = keys
            .into_iter()
            .map(|(key, field, key_type, _)| (key, field, key_type.unwrap_or(KeyType::Text)))
            .collect();
        Ok(())
    }
}

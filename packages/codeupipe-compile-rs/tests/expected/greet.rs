//! Written by codeupipe-compile from GreetPipeline. Do not edit it: compile again.
//!
//! Plain Rust, with no codeupipe: a struct with one field for each key that
//! the steps use, and one function for each step. It has no State and no
//! Hooks. A Tap failure does not stop the run.
/// The error of a step.
pub type StepError = Box<dyn std::error::Error + Send + Sync>;
/// The data of GreetPipeline: one field for each key that its steps use.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct GreetData {
    /// The key "name".
    pub name: Option<String>,
    /// The key "vip".
    pub vip: Option<String>,
    /// The key "note".
    pub note: Option<String>,
    /// The key "badge".
    pub badge: Option<String>,
}
/// The data while the steps of GreetPipeline run. Text that no step has
/// written yet is the caller's, borrowed and not copied.
struct GreetWork<'a> {
    name: Option<::std::borrow::Cow<'a, str>>,
    vip: Option<::std::borrow::Cow<'a, str>>,
    note: Option<::std::borrow::Cow<'a, str>>,
    badge: Option<::std::borrow::Cow<'a, str>>,
}
/// TrimNameFilter
fn cup_01_trim_name_filter(payload: &mut GreetWork<'_>) -> Result<(), StepError> {
    let name = payload.name.as_deref().unwrap_or("").trim().to_string();
    payload.name = Some(::std::borrow::Cow::Owned(::core::convert::Into::into(name)));
    Ok(())
}
/// VipPredicate
fn cup_02_when_vip_predicate(payload: &GreetWork<'_>) -> bool {
    payload.vip.is_some()
}
/// NoteFilter
fn cup_02_note_filter(payload: &mut GreetWork<'_>) -> Result<(), StepError> {
    let name = payload.name.as_deref().unwrap_or("");
    payload.note = Some(::std::borrow::Cow::Owned(::core::convert::Into::into(
        format!("VIP guest {name}"),
    )));
    payload.badge = Some(::std::borrow::Cow::Owned(::core::convert::Into::into(
        "gold",
    )));
    Ok(())
}
/// Runs the steps of GreetPipeline, in order. The caller's text is read where
/// it is: only the text that no step wrote is copied into the output.
pub fn run(input: &GreetData) -> Result<GreetData, StepError> {
    let mut payload = GreetWork {
        name: input.name.as_deref().map(::std::borrow::Cow::Borrowed),
        vip: input.vip.as_deref().map(::std::borrow::Cow::Borrowed),
        note: input.note.as_deref().map(::std::borrow::Cow::Borrowed),
        badge: input.badge.as_deref().map(::std::borrow::Cow::Borrowed),
    };
    cup_01_trim_name_filter(&mut payload)?;
    if cup_02_when_vip_predicate(&payload) {
        cup_02_note_filter(&mut payload)?;
    }
    Ok(GreetData {
        name: payload.name.map(::std::borrow::Cow::into_owned),
        vip: payload.vip.map(::std::borrow::Cow::into_owned),
        note: payload.note.map(::std::borrow::Cow::into_owned),
        badge: payload.badge.map(::std::borrow::Cow::into_owned),
    })
}

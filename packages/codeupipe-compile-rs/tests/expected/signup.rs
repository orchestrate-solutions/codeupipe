//! Written by codeupipe-compile from SignupPipeline. Do not edit it: compile again.
//!
//! Plain Rust, with no codeupipe: a struct with one field for each key that
//! the steps use, and one function for each step. It has no State and no
//! Hooks. A Tap failure does not stop the run.
/// The error of a step.
pub type StepError = Box<dyn std::error::Error + Send + Sync>;
/// The data of SignupPipeline: one field for each key that its steps use.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct SignupData {
    /// The key "email".
    pub email: Option<String>,
    /// The key "welcome".
    pub welcome: Option<bool>,
    /// The key "message".
    pub message: Option<String>,
    /// The key "coupon".
    pub coupon: Option<String>,
    /// The key "discount".
    pub discount: Option<f64>,
}
/// NormalizeEmailFilter
fn cup_01_normalize_email_filter(payload: &mut SignupData) -> Result<(), StepError> {
    let email = payload.email.as_deref().unwrap_or("").trim().to_lowercase();
    if email.is_empty() {
        return Err("there is no email".into());
    }
    payload.email = Some(::core::convert::Into::into(email));
    Ok(())
}
/// WelcomeFilter
fn cup_02_welcome_filter(payload: &mut SignupData) -> Result<(), StepError> {
    payload.welcome = Some(::core::convert::Into::into(true));
    payload.message = Some(::core::convert::Into::into(format!(
        "{}!",
        String::from("Welcome")
    )));
    Ok(())
}
/// HasKeyPredicate
fn cup_03_when_has_key_predicate(payload: &SignupData) -> bool {
    payload.coupon.is_some()
}
/// ApplyCouponFilter
fn cup_03_apply_coupon_filter(payload: &mut SignupData) -> Result<(), StepError> {
    payload.coupon = None;
    payload.discount = Some(::core::convert::Into::into(5.0));
    Ok(())
}
/// CountTap
fn cup_04_count_tap(payload: &SignupData) -> Result<(), StepError> {
    std::hint::black_box(payload.welcome);
    Ok(())
}
/// Runs the steps of SignupPipeline, in order, on a copy of `input`.
pub fn run(input: &SignupData) -> Result<SignupData, StepError> {
    let mut payload = input.clone();
    cup_01_normalize_email_filter(&mut payload)?;
    cup_02_welcome_filter(&mut payload)?;
    if cup_03_when_has_key_predicate(&payload) {
        cup_03_apply_coupon_filter(&mut payload)?;
    }
    let _ = cup_04_count_tap(&payload);
    Ok(payload)
}

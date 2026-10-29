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
/// The data while the steps of SignupPipeline run. Text that no step has
/// written yet is the caller's, borrowed and not copied.
struct SignupWork<'a> {
    email: Option<::std::borrow::Cow<'a, str>>,
    welcome: Option<bool>,
    message: Option<::std::borrow::Cow<'a, str>>,
    coupon: Option<::std::borrow::Cow<'a, str>>,
    discount: Option<f64>,
}
/// The setting `text` of WelcomeFilter, made once and not at each run.
fn cup_02_welcome_filter_text() -> &'static String {
    static VALUE: ::std::sync::OnceLock<String> = ::std::sync::OnceLock::new();
    VALUE.get_or_init(|| String::from("Welcome"))
}
/// NormalizeEmailFilter
fn cup_01_normalize_email_filter(payload: &mut SignupWork<'_>) -> Result<(), StepError> {
    let email = payload.email.as_deref().unwrap_or("").trim().to_lowercase();
    if email.is_empty() {
        return Err("there is no email".into());
    }
    payload.email = Some(::std::borrow::Cow::Owned(::core::convert::Into::into(
        email,
    )));
    Ok(())
}
/// WelcomeFilter
fn cup_02_welcome_filter(payload: &mut SignupWork<'_>) -> Result<(), StepError> {
    payload.welcome = Some(::core::convert::Into::into(true));
    payload.message = Some(::std::borrow::Cow::Owned(::core::convert::Into::into(
        format!("{}!", (*cup_02_welcome_filter_text())),
    )));
    Ok(())
}
/// HasKeyPredicate
fn cup_03_when_has_key_predicate(payload: &SignupWork<'_>) -> bool {
    payload.coupon.is_some()
}
/// ApplyCouponFilter
fn cup_03_apply_coupon_filter(payload: &mut SignupWork<'_>) -> Result<(), StepError> {
    payload.coupon = None;
    payload.discount = Some(::core::convert::Into::into(5.0));
    Ok(())
}
/// CountTap
fn cup_04_count_tap(payload: &SignupWork<'_>) -> Result<(), StepError> {
    std::hint::black_box(payload.welcome);
    Ok(())
}
/// Runs the steps of SignupPipeline, in order. The caller's text is read where
/// it is: only the text that no step wrote is copied into the output.
pub fn run(input: &SignupData) -> Result<SignupData, StepError> {
    let mut payload = SignupWork {
        email: input.email.as_deref().map(::std::borrow::Cow::Borrowed),
        welcome: input.welcome,
        message: input.message.as_deref().map(::std::borrow::Cow::Borrowed),
        coupon: input.coupon.as_deref().map(::std::borrow::Cow::Borrowed),
        discount: input.discount,
    };
    cup_01_normalize_email_filter(&mut payload)?;
    cup_02_welcome_filter(&mut payload)?;
    if cup_03_when_has_key_predicate(&payload) {
        cup_03_apply_coupon_filter(&mut payload)?;
    }
    let _ = cup_04_count_tap(&payload);
    Ok(SignupData {
        email: payload.email.map(::std::borrow::Cow::into_owned),
        welcome: payload.welcome,
        message: payload.message.map(::std::borrow::Cow::into_owned),
        coupon: payload.coupon.map(::std::borrow::Cow::into_owned),
        discount: payload.discount,
    })
}

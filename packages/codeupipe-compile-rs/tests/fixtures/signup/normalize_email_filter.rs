use codeupipe::{Filter, Payload, StepError, Value};

/// Trims the email and makes it lower case. With no email, the run fails.
pub struct NormalizeEmailFilter;

impl Filter for NormalizeEmailFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let email = payload
            .get("email")
            .and_then(Value::as_str)
            .unwrap_or("")
            .trim()
            .to_lowercase();
        if email.is_empty() {
            return Err("there is no email".into());
        }
        payload.insert("email", email);
        Ok(())
    }
}

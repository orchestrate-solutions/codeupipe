use codeupipe::{Filter, Payload, StepError};

pub struct WelcomeFilter {
    text: String,
}

impl WelcomeFilter {
    pub fn new(text: &str) -> Self {
        WelcomeFilter {
            text: String::from(text),
        }
    }
}

impl Filter for WelcomeFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("welcome", true);
        payload.insert("message", format!("{}!", self.text));
        Ok(())
    }
}

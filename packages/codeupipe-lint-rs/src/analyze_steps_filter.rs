use codeupipe::{Filter, StepError};
use syn::visit::Visit;

use crate::lint_run::LintRun;
use crate::step_visitor::StepVisitor;

/// CUP-A003 and CUP-A005: a step whose type is declared in a function, and
/// a plain `Pipeline` nested as a step.
///
/// A step is the argument of `add_filter`, `add_tap` or `add_pipeline` (on
/// any receiver), or one of the two arguments of `add_valve(predicate,
/// filter)`. A name is followed to the `let` that gave its value, in the
/// same function. A parameter and a name from another file are not followed.
///
/// A closure or a function as a step (CUP-A001, A002, A008) is a compile
/// error in Rust, so it has no rule here.
///
/// Reads `sources`. Writes `findings`.
pub struct AnalyzeStepsFilter;

impl Filter<LintRun> for AnalyzeStepsFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        for source in &run.sources {
            let mut visitor = StepVisitor::new(source);
            visitor.visit_file(&source.tree);
            run.findings.append(&mut visitor.findings);
        }
        Ok(())
    }
}

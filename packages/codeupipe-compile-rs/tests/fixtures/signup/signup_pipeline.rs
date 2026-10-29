use codeupipe::{NamedPipeline, Pipeline};

use super::apply_coupon_filter::ApplyCouponFilter;
use super::count_tap::CountTap;
use super::has_key_predicate::HasKeyPredicate;
use super::normalize_email_filter::NormalizeEmailFilter;
use super::welcome_filter::WelcomeFilter;

pub struct SignupPipeline;

impl NamedPipeline for SignupPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(NormalizeEmailFilter);
        pipeline.add_filter(WelcomeFilter::new("Welcome"));
        pipeline.add_valve(HasKeyPredicate::new("coupon"), ApplyCouponFilter::new(5.0));
        pipeline.add_tap(CountTap);
    }
}

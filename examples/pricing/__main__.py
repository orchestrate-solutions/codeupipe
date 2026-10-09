"""python -m examples.pricing: run the pipeline with a Hook and show its State."""

from codeupipe import Payload

from .pricing_pipeline import PricingPipeline
from .print_steps_hook import PrintStepsHook

pipeline = PricingPipeline()
pipeline.use_hook(PrintStepsHook())

print("steps:")
result = pipeline.run(Payload({"price": 100.0, "qty": 12}))

print("result:  ", result.to_dict())
print("executed:", pipeline.state.executed)
print("skipped: ", pipeline.state.skipped)
print("errors:  ", pipeline.state.errors)

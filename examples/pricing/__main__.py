"""python -m examples.pricing: run the pipeline with a Hook and show its State."""

from codeupipe import Payload

from .pipeline import build_pricing
from .print_steps import PrintSteps

pipeline = build_pricing()
pipeline.use_hook(PrintSteps())

print("steps:")
result = pipeline.run(Payload({"price": 100.0, "qty": 12}))

print("result:  ", result.to_dict())
print("executed:", pipeline.state.executed)
print("skipped: ", pipeline.state.skipped)
print("errors:  ", pipeline.state.errors)

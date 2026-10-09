"""python -m examples: run the pricing pipeline and show its State."""

from codeupipe import Payload

from examples.pricing import build_pricing

pipeline = build_pricing()
print(pipeline.run(Payload({"price": 100.0, "qty": 12})).to_dict())
print("executed:", pipeline.state.executed)
print("errors:  ", pipeline.state.errors)

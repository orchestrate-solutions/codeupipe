"""A small pipeline, one primitive in each file.

    discount_filter.py      Filter     takes the Payload, writes to it, returns it
    mark_bulk_filter.py     Filter
    at_least_predicate.py   Predicate  a yes-or-no question; the pipeline joins it to a Filter with add_valve
    audit_tap.py            Tap        reads the Payload; if it fails, State records it and the run goes on
    print_steps_hook.py     Hook       sees each step start
    pricing_pipeline.py     Pipeline   where they come together

A class name ends with its role, and its file name is the class name in
snake_case.

Each part knows nothing about the others, so each can be tested alone and
used again in another pipeline.

Run it:      python -m examples.pricing
Compile it:   python -m codeupipe.compile examples.pricing.pricing_pipeline:PricingPipeline --out build/pricing
"""

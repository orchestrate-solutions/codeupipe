"""A small pipeline, one primitive in each file.

    discount.py      Filter     takes the Payload, writes to it, returns it
    mark_bulk.py     Filter
    at_least.py      predicate  the question a Valve asks
    audit_tap.py     Tap        reads the Payload; its failure never halts the run
    print_steps.py   Hook       sees each step start
    pipeline.py      Pipeline   where they come together

Each part knows nothing about the others, so each can be tested alone and
used again in another pipeline.

Run it:      python -m examples.pricing
Export it:   python -m codeupipe.lower examples.pricing.pipeline:build_pricing --out build/pricing
"""

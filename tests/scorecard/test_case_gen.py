import json
import random

from scorecard import case_gen, vocab


def test_same_seed_same_cases():
    assert case_gen.generate_cases(7, 30) == case_gen.generate_cases(7, 30)


def test_different_seed_different_cases():
    assert case_gen.generate_cases(7, 30) != case_gen.generate_cases(8, 30)


def test_cases_are_json_round_trippable():
    for case in case_gen.generate_cases(3, 50):
        assert json.loads(json.dumps(case)) == case


def test_corpus_covers_the_whole_vocabulary():
    seen_filter, seen_tap, seen_when, kinds = set(), set(), set(), set()
    hooks = False
    for case in case_gen.generate_cases(11, 300):
        hooks = hooks or case["hooks"]
        for step in vocab.walk_steps(case["steps"]):
            kinds.add(step["kind"])
            if step["kind"] == "filter":
                seen_filter.add(step["op"])
            elif step["kind"] == "tap":
                seen_tap.add(step["op"])
            elif step["kind"] == "valve":
                seen_when.add(step["when"]["op"])
                seen_filter.add(step["filter"]["op"])
    assert seen_filter == set(case_gen.FILTER_OPS)
    assert seen_tap == set(case_gen.TAP_OPS)
    assert seen_when == {"equals", "truthy"}
    assert kinds == {"filter", "tap", "valve", "pipeline"}
    assert hooks


def test_some_cases_cross_the_payload_flattening_depth():
    longest = max(len(list(vocab.walk_steps(c["steps"]))) for c in case_gen.generate_cases(5, 300))
    assert longest > 32


def test_hostile_names_only_when_asked():
    plain = case_gen.generate_cases(1, 100, hostile_rate=0.0)
    names = {s["name"] for c in plain for s in vocab.walk_steps(c["steps"])}
    assert not names & set(case_gen.HOSTILE_NAMES)
    hostile = case_gen.generate_cases(1, 100, hostile_rate=1.0)
    names = {s["name"] for c in hostile for s in vocab.walk_steps(c["steps"])}
    assert names & set(case_gen.HOSTILE_NAMES)


def test_every_generated_case_builds_and_runs_dynamically():
    for case in case_gen.generate_cases(2, 40, hostile_rate=0.5):
        predicates = vocab.make_predicates(case["steps"], vocab.new_workdir())
        pipeline = vocab.build_pipeline(case, predicates)
        try:
            pipeline.run(vocab.Payload(dict(case["input"])))
        except Exception:  # noqa: BLE001 — failing filters are part of the vocabulary
            pass


def test_generate_value_is_json_shaped():
    rng = random.Random(0)
    for _ in range(200):
        value = case_gen.generate_value(rng)
        assert json.loads(json.dumps(value)) == value

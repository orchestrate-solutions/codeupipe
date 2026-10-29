from codeupipe import Payload
from codeupipe_add.stale_pipelines_filter import StalePipelinesFilter

GIVEN = '''class PricingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.add_filter(DiscountFilter(0.1))
        self.add_tap(AuditTap())
'''


def pricing(calls):
    return {"kind": "pipeline", "component_path": "app/pricing_pipeline.py",
            "component_text": "class PricingPipeline(Pipeline):\n" + "".join("        %s\n" % call for call in calls)}


def stale(root, component, kept):
    return StalePipelinesFilter().call(Payload({"root": str(root), "components": [component],
                                                "kept": kept})).get("stale")


def test_a_kept_pipeline_with_the_steps_of_the_layout_is_not_stale_even_with_arguments_and_comments(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "pricing_pipeline.py").write_text(GIVEN.replace("        self.add_tap", "        # Audit.\n"
                                                                                    "        self.add_tap"))
    component = pricing(["self.add_filter(DiscountFilter())", "self.add_tap(AuditTap())"])
    assert stale(tmp_path, component, ["app/pricing_pipeline.py"]) == []


def test_a_kept_pipeline_whose_steps_are_not_those_of_the_layout_is_stale(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "pricing_pipeline.py").write_text(GIVEN)
    component = pricing(["self.add_filter(DiscountFilter())", "self.add_valve(GiftPredicate(), GiftFilter())",
                         "self.add_tap(AuditTap())"])
    assert stale(tmp_path, component, ["app/pricing_pipeline.py"]) == ["app/pricing_pipeline.py"]


def test_a_pipeline_that_was_written_now_or_a_kept_file_that_is_not_a_pipeline_is_not_looked_at(tmp_path):
    component = pricing(["self.add_filter(DiscountFilter())"])
    assert stale(tmp_path, component, []) == []
    assert stale(tmp_path, dict(component, kind="filter"), ["app/pricing_pipeline.py"]) == []

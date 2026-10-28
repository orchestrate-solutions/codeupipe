"""JudgeResultsFilter: compare what each target reported with what each case expects.

This is the one place that decides pass or fail. A verdict is a status and
its problems:

    pass         every expectation matched
    partial      every expectation that the target can show matched, but it
                 does not show some of them at all (the fast compiled forms
                 show no State and no Hooks)
    FAIL         something that the target shows is different
    unsupported  the target cannot express the case. Never counted as a pass
"""

from codeupipe import Payload

# What a target may not show at all. A case that expects one of these, on a target that does not report it, is "partial".
_NOT_ALWAYS_SHOWN = ("state", "hooks", "inner_states", "pipeline_state")


class JudgeResultsFilter:
    """Filter (sync).

    Input keys: ``cases``, ``results`` ({name: {case id: result}}).
    Output keys: ``verdicts`` ({name: {case id: (status, problems)}}).
    """

    def call(self, payload: Payload) -> Payload:
        cases = payload.get("cases")
        verdicts = {name: {case["id"]: self.judge(case, found.get(case["id"])) for case in cases}
                    for name, found in payload.get("results").items()}
        return payload.insert("verdicts", verdicts)

    def judge(self, case, result):
        """The verdict for one case on one target: ``(status, problems)``."""
        if result is None:
            return "FAIL", ["no result from runner"]
        if "unsupported" in result:
            return "unsupported", [result["unsupported"]]
        expect = case["expect"]
        problems = self.output_problems(expect, result)

        if self.norm(result.get("input_after")) != self.norm(case["input"]):
            problems.append(f"input was mutated: {result.get('input_after')!r}")

        if "taps" in expect and self.norm(result.get("taps")) != self.norm(expect["taps"]):
            problems.append(f"taps {result.get('taps')!r} != {expect['taps']!r}")

        if "state" in expect and "state" in result:
            for key, want in expect["state"].items():
                got = result["state"].get(key)
                if got != want:
                    problems.append(f"state.{key} {got!r} != {want!r}")

        for key in ("inner_states", "pipeline_state"):
            if key in expect and key in result and result[key] != expect[key]:
                problems.append(f"{key} {result[key]!r} != {expect[key]!r}")

        if "hooks" in expect and "hooks" in result and result["hooks"] != expect["hooks"]:
            problems.append(f"hooks {result['hooks']!r} != {expect['hooks']!r}")

        if problems:
            return "FAIL", problems
        unchecked = [key for key in _NOT_ALWAYS_SHOWN if key in expect and key not in result]
        if unchecked:
            return "partial", [f"target cannot observe {', '.join(unchecked)}"]
        return "pass", []

    def output_problems(self, expect, result) -> list:
        """What is wrong with the output or the error of a run."""
        problems = []
        if "output" in expect:
            if "error" in result:
                problems.append(f"expected output, got error {result['error']!r}")
            elif self.norm(result.get("output")) != self.norm(expect["output"]):
                problems.append(f"output {result.get('output')!r} != {expect['output']!r}")
        if "error" in expect:
            if "error" not in result:
                problems.append(f"expected an error, got output {result.get('output')!r}")
            elif expect["error"].get("message_contains", "") not in result["error"]:
                problems.append(f"error {result['error']!r} lacks {expect['error']['message_contains']!r}")
        return problems

    def norm(self, value):
        """JSON equality: 1 == 1.0, but true is not 1."""
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, list):
            return [self.norm(v) for v in value]
        if isinstance(value, dict):
            return {k: self.norm(v) for k, v in value.items()}
        return value

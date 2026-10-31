"""JudgeAddFilter: compare what ``codeupipe add`` did with what each case expects.

The one place that decides pass or fail for the cases of ``add``
(conformance/ADD.md). A verdict is ``pass`` or ``FAIL``, with its problems.
"""

import re

from codeupipe import Payload

RED_MESSAGE = "Write the acceptance case for %s."


class JudgeAddFilter:
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
            return "FAIL", ["no result from the launcher"]
        expect, lang = case["expect"], result["lang"]
        files = expect["files"][lang]
        problems = []
        if result["exit"] != expect["exit"]:
            problems.append("exit %s, expected %s: %s" % (result["exit"], expect["exit"], result["stderr"].strip()[-500:]))
        if result["printed"] != files:
            problems.append("printed %r, expected %r" % (result["printed"], files))
        if result["created"] != sorted(files):
            problems.append("made the files %r, expected %r" % (result["created"], sorted(files)))
        if result["changed"]:
            problems.append("changed a file that was there: %r" % result["changed"])
        wanted = expect.get("message_contains")
        if wanted and wanted not in result["stderr"]:
            problems.append("stderr %r lacks %r" % (result["stderr"].strip()[-500:], wanted))
        if expect["exit"] == 0 and not problems:
            problems.extend(self.made_problems(expect, result))
        return ("FAIL", problems) if problems else ("pass", [])

    def made_problems(self, expect, result) -> list:
        """What is wrong with the files of a run that made them: each component, in order."""
        types = expect.get("types") or [expect["type"]]
        made = result.get("made", [])
        if len(made) != len(types):
            return ["made %d components, expected %d: %s" % (len(made), len(types), ", ".join(types))]
        problems = []
        for type_name, found in zip(types, made):
            problems.extend(self.component_problems(type_name, found))
        for text in expect.get("contains", []):
            if text not in made[0]["text"]:
                problems.append("the component file lacks %r" % text)
        for type_name, steps in expect.get("steps", {}).items():
            text = made[types.index(type_name)]["text"]
            if not self.in_order(text[text.rfind(type_name) + len(type_name):], steps):
                problems.append("the steps of %s are not %s, in order:\n%s" % (type_name, ", ".join(steps), text))
        return problems

    def component_problems(self, type_name, found) -> list:
        """What is wrong with one component file, its lint, and its test."""
        problems = []
        if not re.search(r"\b%s\b" % re.escape(type_name), found["text"]):
            problems.append("%s does not declare %s" % (found["component"], type_name))
        for lint in found["lint"]:
            if lint["exit"] != 0 or (lint["quiet"] and lint["output"].strip()):
                problems.append("lint `%s` (exit %s): %s" % (lint["cmd"], lint["exit"], lint["output"].strip()[-800:]))
        test, message = found.get("test"), RED_MESSAGE % type_name
        if test is None:
            problems.append("the test of %s did not run" % type_name)
        elif test["exit"] == 0:
            problems.append("the test of %s passed: it must fail with %r" % (type_name, message))
        elif message not in test["output"]:
            problems.append("the test failed, but not with %r: %s" % (message, test["output"].strip()[-800:]))
        return problems

    def in_order(self, text, names) -> bool:
        """Each name is in text, after the one before it. The text starts after the last mention of the pipeline type, so
        the imports and the header comment do not count."""
        at = 0
        for name in names:
            found = re.search(r"\b%s\b" % re.escape(name), text[at:])
            if not found:
                return False
            at += found.end()
        return True

"""SummarizeFilter: the counts for each target, the matrix, and the exit code."""

from codeupipe import Payload


class SummarizeFilter:
    """Filter (sync).

    Input keys: ``cases``, ``names``, ``verdicts``, ``target_errors``.
    Output keys: ``report`` (the number of cases, and for each target its
    counts, its failures and the cases that it cannot express, or the
    reason that it did not run), ``matrix`` ({case id: {name: status}}) and
    ``exit_code`` (1 when a case failed or a target did not run).
    """

    def call(self, payload: Payload) -> Payload:
        cases, verdicts, errors = payload.get("cases"), payload.get("verdicts"), payload.get("target_errors")
        report = {"cases": len(cases), "targets": {}}
        matrix = {case["id"]: {} for case in cases}
        for name in payload.get("names"):
            if name in errors:
                report["targets"][name] = {"error": errors[name]}
                for case in cases:
                    matrix[case["id"]][name] = "—"
                continue
            summary = {"pass": 0, "partial": 0, "FAIL": 0, "unsupported": 0, "failures": {}, "unsupported_cases": {}}
            for case in cases:
                status, problems = verdicts[name][case["id"]]
                summary[status] += 1
                matrix[case["id"]][name] = status
                if status == "FAIL":
                    summary["failures"][case["id"]] = problems
                elif status == "unsupported":
                    summary["unsupported_cases"][case["id"]] = problems[0]
            report["targets"][name] = summary
        failed = any(target.get("FAIL") or "error" in target for target in report["targets"].values())
        return payload.insert("report", report).insert("matrix", matrix).insert("exit_code", 1 if failed else 0)

"""FormatMatrixFilter: the matrix and the counts as Markdown."""

from codeupipe import Payload

_MARK = {"pass": "✅", "partial": "✅*", "FAIL": "❌", "unsupported": "➖", "—": "—"}


class FormatMatrixFilter:
    """Filter (sync).

    Input keys: ``cases``, ``names``, ``matrix``, ``report``.
    Output keys: ``markdown``.
    """

    def call(self, payload: Payload) -> Payload:
        cases, names = payload.get("cases"), payload.get("names")
        matrix, report = payload.get("matrix"), payload.get("report")
        lines = ["| case | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
        for case in cases:
            lines.append(f"| `{case['id']}` | " + " | ".join(_MARK[matrix[case['id']][n]] for n in names) + " |")
        lines.append("")
        for name in names:
            target = report["targets"][name]
            if "error" in target:
                lines.append(f"- **{name}**: not run: {target['error']}")
            else:
                lines.append(f"- **{name}**: {target['pass']} pass, {target['partial']} pass*, {target['FAIL']} fail, "
                             f"{target['unsupported']} unsupported")
        lines.append("")
        lines.append("✅* passed everything the target can observe; it does not expose State or Hooks "
                     "(the fast mode). ➖ the target cannot express the case.")
        return payload.insert("markdown", "\n".join(lines) + "\n")

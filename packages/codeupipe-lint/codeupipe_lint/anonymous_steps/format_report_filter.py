"""FormatReportFilter: the findings as sorted report lines, and the exit code."""

from codeupipe import Payload


class FormatReportFilter:
    """Filter (sync).

    Input keys: ``findings``, ``suppressed``, ``errors``, optional ``strict``.
    Output keys: ``findings`` (sorted), ``report`` (stdout text),
    ``error_report`` (stderr text), ``exit_code``: 0 clean, 1 anonymous
    steps found, 2 a path could not be read (the check is incomplete).
    ``noun`` and ``plural`` name what a finding is; other linters pass their own.

    A warning is in the report and is counted apart. It does not make the
    exit code 1, unless ``strict`` is true.
    """

    def __init__(self, noun="anonymous step", plural="anonymous steps"):
        self.noun = noun
        self.plural = plural

    def call(self, payload: Payload) -> Payload:
        findings = sorted(payload.get("findings", []), key=lambda f: (f.path, f.line, f.col, f.rule))
        suppressed = payload.get("suppressed", [])
        errors = payload.get("errors", [])
        lines = [f.format() for f in findings]
        warnings = sum(1 for f in findings if f.severity == "warning")
        real = len(findings) - warnings
        if real:
            summary = "%d %s" % (real, self.noun if real == 1 else self.plural)
        else:
            summary = "No %s" % self.plural
        if suppressed:
            summary += " (%d suppressed)" % len(suppressed)
        summary += "."
        if warnings:
            summary += " %d %s." % (warnings, "warning" if warnings == 1 else "warnings")
        lines.append(summary)
        fails = real or (warnings and payload.get("strict") is True)
        exit_code = 2 if errors else (1 if fails else 0)
        error_report = "\n".join("error: " + e for e in errors)
        return (payload.insert("findings", findings).insert("report", "\n".join(lines))
                .insert("error_report", error_report).insert("exit_code", exit_code))

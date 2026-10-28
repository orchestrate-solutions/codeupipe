"""RunTargetsFilter: run the cases on each target."""

from codeupipe import Payload


class RunTargetsFilter:
    """Filter (sync).

    Input keys: ``names`` (the targets to run, in order), ``targets``
    ({name: how to start its runner}), ``cases``.
    Output keys: ``results`` ({name: {case id: result}}) for each target that
    ran, and ``target_errors`` ({name: reason}) for each one that did not.

    ``launcher`` runs one target: ``launcher.run(spec, cases)``.
    """

    def __init__(self, launcher):
        self.launcher = launcher

    def call(self, payload: Payload) -> Payload:
        targets, cases = payload.get("targets"), payload.get("cases")
        results, errors = {}, {}
        for name in payload.get("names"):
            found, error = self.launcher.run(targets[name], cases)
            if error:
                errors[name] = error
            else:
                results[name] = found
        return payload.insert("results", results).insert("target_errors", errors)

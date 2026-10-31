"""AddLauncher: plays the cases of ``codeupipe add`` for one target, and reports what it saw."""

import hashlib
import os
import pathlib
import re
import subprocess
import sys
import tempfile

# A note on stderr that asks for a line in another file: ``add to src/lib.rs: pub mod discount_filter;``.
_REGISTER = re.compile(r"^add to (\S+): (.+)$")

# Files that a build or a test makes on its own. They are not files that the command made.
_NOT_MADE = ("__pycache__", ".pytest_cache", "target", "node_modules")


# cup: allow-plain the edge to the commands: it makes a project, runs the command, the linter and the test, and reads what happened
class AddLauncher:
    """Runs the ``add`` command of one target on each case. ``spec`` is the
    target, as its file in ``conformance/add/targets/`` has it.

    Gives ``(results, None)``, with ``results`` as {case id: result}, or
    ``(None, reason)`` when the target cannot be used. A result is what
    happened, never a verdict: JudgeAddFilter decides.
    """

    def __init__(self, repo):
        self.repo = pathlib.Path(repo)

    def run(self, spec, cases):
        results = {}
        for case in cases:
            with tempfile.TemporaryDirectory(prefix="cup-add-") as project:
                results[case["id"]] = self.play(spec, case, pathlib.Path(project))
        return results, None

    def play(self, spec, case, project):
        lang = spec["lang"]
        for path, text in spec.get("setup", {}).items():
            self.write(project / path, self.fill(text, project))
        given = case.get("given", {}).get(lang, {})
        for path, text in given.items():
            self.write(project / path, text)
        layout = case.get("layout")
        if layout:
            # One layout for each language: only its lang: changes.
            self.write(project / layout["path"], layout["text"].replace("{lang}", lang))
        before = self.snapshot(project)
        ran = self.command(spec["cmd"] + case["args"], spec.get("env", {}), project)
        after = self.snapshot(project)
        result = {
            "id": case["id"], "lang": lang, "exit": ran.returncode,
            "printed": [line for line in ran.stdout.splitlines() if line.strip()],
            "stderr": ran.stderr,
            "created": sorted(set(after) - set(before)),
            "changed": sorted(path for path in given if before.get(path) != after.get(path)),
        }
        if ran.returncode != 0 or not result["printed"]:
            return result
        self.register(ran.stderr, project)
        printed = result["printed"] + [""] * (len(result["printed"]) % 2)
        # The command prints each component file, then its test: one pair for each component it made.
        result["made"] = [self.made(spec, project, component, test)
                          for component, test in zip(printed[0::2], printed[1::2])]
        return result

    def made(self, spec, project, component, test):
        """The file, the lint and the test of one component that the command made."""
        path = project / component
        names = {"component": component, "test": test, "test_stem": pathlib.Path(test).stem,
                 "component_dir": str(pathlib.Path(component).parent)}
        return {"component": component, "text": path.read_text() if path.is_file() else "",
                "lint": [self.check(step, project, names) for step in spec.get("lint", [])],
                "test": self.check(spec["test"], project, names)}

    def register(self, stderr, project):
        """Add each line that the command asks for on stderr, as a user would."""
        for line in stderr.splitlines():
            found = _REGISTER.match(line.strip())
            if found:
                target = project / found.group(1)
                text = target.read_text() if target.exists() else ""
                self.write(target, text + ("" if text.endswith("\n") or not text else "\n") + found.group(2) + "\n")

    def check(self, step, project, names):
        argv = [self.fill(part, project, names) for part in step["cmd"]]
        ran = self.command(argv, step.get("env", {}), project)
        output = ran.stdout + ran.stderr
        return {"cmd": " ".join(argv), "exit": ran.returncode, "output": output[-4000:],
                "quiet": bool(step.get("quiet"))}

    def command(self, argv, env, project):
        full = dict(os.environ)
        full.update({key: self.fill(value, project) for key, value in env.items()})
        argv = [self.fill(part, project) for part in argv]
        try:
            return subprocess.run(argv, cwd=project, env=full, capture_output=True, text=True, timeout=600)
        except FileNotFoundError as error:
            return subprocess.CompletedProcess(argv, 127, "", "cannot run %s: %s" % (argv[0], error))

    def fill(self, text, project, names=None):
        values = {"repo": str(self.repo), "project": str(project), "python": sys.executable,
                  "pathsep": os.pathsep}
        values.update(names or {})
        for key, value in values.items():
            text = text.replace("{%s}" % key, value)
        return text

    def snapshot(self, project):
        """{relative path: hash of the contents} of each file in the project."""
        files = {}
        for path in project.rglob("*"):
            relative = path.relative_to(project)
            if path.is_file() and not any(part in _NOT_MADE for part in relative.parts):
                files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return files

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

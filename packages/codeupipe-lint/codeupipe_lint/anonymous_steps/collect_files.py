"""CollectFiles: the source files under the given paths, grouped by language."""

import fnmatch
import os

from codeupipe import Payload

EXTENSIONS = {
    ".py": "python",
    ".go": "go",
    ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".cts": "ts",
    ".rs": "rust",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".hxx": "cpp", ".h": "cpp",
    ".kt": "kotlin", ".kts": "kotlin",
    ".cs": "csharp",
}
SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", "bin", "obj", "__pycache__", ".gradle",
             ".venv", ".idea", ".pytest_cache"}


def language_of(path: str):
    if path.endswith(".d.ts"):
        return None
    return EXTENSIONS.get(os.path.splitext(path)[1])


class CollectFiles:
    """Filter (sync).

    Input keys: ``paths`` (files or directories), optional ``languages``,
    optional ``exclude`` (fnmatch globs matched against each file's path).
    Output keys: ``files`` ({lang: [path]}), ``errors`` (list, appended).
    Directories are walked, skipping VCS, dependency and build-output
    directories (SKIP_DIRS, and ``.venv*``); a file named explicitly is taken.
    """

    def call(self, payload: Payload) -> Payload:
        languages = payload.get("languages")
        exclude = payload.get("exclude") or []
        errors = list(payload.get("errors", []))
        files = {}

        def take(path):
            lang = language_of(path)
            if any(fnmatch.fnmatch(path, pattern) for pattern in exclude):
                return
            if lang and (not languages or lang in languages):
                files.setdefault(lang, []).append(path)

        for root in payload.get("paths", []):
            if os.path.isfile(root):
                take(root)
            elif os.path.isdir(root):
                for dirpath, dirnames, filenames in os.walk(root):
                    dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".venv"))
                    for name in sorted(filenames):
                        take(os.path.join(dirpath, name))
            else:
                errors.append("%s: no such file or directory" % root)
        return payload.insert("files", files).insert("errors", errors)

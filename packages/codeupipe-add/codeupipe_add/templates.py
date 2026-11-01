"""The text of each file that ``codeupipe add`` makes, for each kind.

``{type_name}``, ``{description}``, ``{module}`` and ``{snake}`` are filled in.
Each component does nothing (conformance/ADD.md); the test fails on purpose.
"""

COMPONENTS = {
    "filter": '''"""{type_name}: {description}"""


class {type_name}:
    """A Filter: it returns the Payload with no change."""

    def call(self, payload):
        return payload
''',
    "predicate": '''"""{type_name}: {description}"""


class {type_name}:
    """A Predicate: its answer is always no."""

    def test(self, payload):
        return False
''',
    "tap": '''"""{type_name}: {description}"""


class {type_name}:
    """A Tap: it reads nothing yet."""

    def observe(self, payload):
        pass
''',
    "hook": '''"""{type_name}: {description}"""

from codeupipe import Hook


class {type_name}(Hook):
    """A Hook: it does nothing at each event."""
''',
    "pipeline": '''"""{type_name}: {description}"""

from codeupipe import Pipeline


class {type_name}(Pipeline):
    """A Pipeline with no steps yet."""

    def __init__(self):
        super().__init__()
''',
}

# A pipeline of a layout, with its steps (conformance/ADD.md, "Phase 2"): {imports} and {calls} are lines.
PIPELINE_STEPS = '''"""{type_name}: {description}"""

from codeupipe import Pipeline

{imports}


class {type_name}(Pipeline):
    """A Pipeline: its steps come from the layout."""

    def __init__(self):
        super().__init__()
{calls}
'''

TEST = '''"""The acceptance case of {type_name}."""

from {module} import {type_name}


def test_{snake}():
    assert {type_name}() is not None
    raise AssertionError("Write the acceptance case for {type_name}.")
'''

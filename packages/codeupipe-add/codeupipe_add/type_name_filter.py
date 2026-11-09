"""TypeNameFilter: the type name, from the kind and the name that were given."""

import re

from codeupipe import Payload

from .refusal import Refusal

ROLES = {"filter": "Filter", "predicate": "Predicate", "tap": "Tap", "hook": "Hook", "pipeline": "Pipeline"}

NOT_MADE = {
    "valve": "A Valve is not a type. Make a Predicate and a Filter, and join them with add_valve(predicate, filter).",
    "payload": "The runtime makes the Payload. A user does not write one.",
    "state": "The runtime makes the State. A user does not write one.",
}

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

# The rule of the linters (CUP-I006): where a word starts in a type name.
WORD_BREAK = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


class TypeNameFilter:
    """Filter (sync).

    Input keys: ``kind``, ``name``.
    Output keys: ``type_name`` (``DiscountFilter``), ``snake``
    (``discount_filter``). A kind or a name that cannot be used is refused with
    exit code 2.
    """

    def call(self, payload: Payload) -> Payload:
        kind, name = payload.get("kind"), payload.get("name")
        if kind in NOT_MADE:
            raise Refusal(2, NOT_MADE[kind])
        if kind not in ROLES:
            raise Refusal(2, "Unknown kind %r. The kinds are: filter, predicate, tap, hook, pipeline." % kind)
        if not name or not _NAME.match(name):
            raise Refusal(2, "The name %r cannot be used. A name starts with a letter, and has only letters, "
                             "digits, _ and -." % name)
        words = re.split(r"[_-]+", name)
        type_name = "".join(word[:1].upper() + word[1:] for word in words if word)
        role = ROLES[kind]
        if not type_name.endswith(role):
            type_name += role
        snake = WORD_BREAK.sub("_", type_name).lower()
        return payload.insert("type_name", type_name).insert("snake", snake)

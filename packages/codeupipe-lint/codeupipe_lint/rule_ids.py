"""Every rule id of the two linters, and the check of a --disable list."""

from typing import Iterable, List

from .anonymous_steps.rules import RULES as ANONYMOUS_RULES
from .invariants.rules import RULES as INVARIANT_RULES

__all__ = ["known_rules", "unknown_rules"]


def known_rules() -> List[str]:
    return sorted(set(ANONYMOUS_RULES) | set(INVARIANT_RULES))


def unknown_rules(rule_ids: Iterable[str]) -> List[str]:
    """The ids in ``rule_ids`` that neither linter has."""
    known = set(known_rules())
    return sorted(set(rule_ids) - known)

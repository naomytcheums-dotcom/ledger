"""
Retention holds -- mark a range of the ledger as not-yet-deletable
before a given date, and refuse a purge that would violate it. Pure
policy logic: this module never deletes anything itself, it only
answers "is this deletion allowed," so it's safe to unit test without
ever touching a real ledger file or a real deletion path.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionHold:
    """`applies_to` is a predicate over a DecisionRecord (e.g. "record
    id starts with the regulated product line's prefix") -- a hold
    doesn't have to cover an entire ledger, just the records it
    actually governs. `until` is an ISO 8601 timestamp string,
    compared the same lexicographic way `query.between` compares
    timestamps."""

    id: str
    until: str
    applies_to: object
    reason: str = ""


class RetentionViolationError(ValueError):
    """Raised by `enforce_retention` -- names every hold blocking the
    deletion, not just the first one, so a caller sees the whole
    picture in one error instead of fixing holds one at a time."""


def check_deletable(record, holds, current_timestamp):
    """Returns the list of holds currently blocking deletion of
    `record` -- holds whose `applies_to(record)` is true and whose
    `until` hasn't passed yet. An empty list means deletion is allowed."""
    return [h for h in holds if h.applies_to(record) and current_timestamp < h.until]


def enforce_retention(record, holds, current_timestamp):
    blocking = check_deletable(record, holds, current_timestamp)
    if blocking:
        reasons = "; ".join(f"{h.id} (until {h.until}): {h.reason}" for h in blocking)
        raise RetentionViolationError(f"cannot delete record {record.id!r}, blocked by: {reasons}")
    return True

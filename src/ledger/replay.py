"""
Verify that a ledger's hash chain is actually intact -- the check that
turns "we have logs" into "we can prove these logs weren't altered
after the fact." Also supports diffing two records that claim to
represent the same logical decision at different points in time.
"""

from ledger.record import GENESIS_HASH


class ChainIntegrityError(ValueError):
    """Raised by `verify_chain` -- names the first record (by index and
    id) whose stored `previous_hash` no longer matches the recomputed
    hash of the record before it."""


def verify_chain(records):
    """Walks `records` in order, recomputing each one's hash and
    checking it links correctly to the previous record. Returns True
    if every record checks out; raises `ChainIntegrityError` naming the
    first broken link otherwise -- silently returning False would let
    a caller ignore exactly the failure this function exists to catch.

    Tampering with a record's own content (without touching anything
    downstream) is detected at the *next* record, not the tampered one
    itself -- its own `previous_hash` field is unaffected by changes to
    its own content, only the hash it produces going forward changes.
    A consequence: tampering with the *most recent* record and then
    continuing to append normally is never detected by this function
    alone -- each new append reads the current (tampered) file and
    chains onto it, so the chain stays internally consistent. Catching
    that case needs an independent checkpoint of the last known-good
    hash, taken before the tampering, which this library doesn't
    provide."""
    expected_previous = GENESIS_HASH
    for index, record in enumerate(records):
        if record.previous_hash != expected_previous:
            raise ChainIntegrityError(
                f"record {index} (id={record.id!r}) has previous_hash "
                f"{record.previous_hash!r}, expected {expected_previous!r} "
                f"-- a record before it was altered, inserted, or deleted"
            )
        expected_previous = record.record_hash()
    return True


def diff_records(a, b):
    """Field-by-field differences between two records claiming to
    represent "the same" decision re-run later -- which of
    model_version/prompt_version/data_snapshot/input/output actually
    changed, useful for explaining why a re-run didn't reproduce the
    original."""
    fields = ("model_version", "prompt_version", "data_snapshot", "input", "output")
    return {f: (getattr(a, f), getattr(b, f)) for f in fields if getattr(a, f) != getattr(b, f)}

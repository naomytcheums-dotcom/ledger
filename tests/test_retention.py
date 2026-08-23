import pytest

from ledger.record import DecisionRecord
from ledger.retention import RetentionHold, RetentionViolationError, check_deletable, enforce_retention


def _make_record(record_id="regulated-001"):
    return DecisionRecord(
        id=record_id, timestamp="2026-08-23T10:00:00Z", model_version="mv1",
        prompt_version="pv1", data_snapshot="ds1", input="q", output="a", previous_hash="0" * 64,
    )


def _hold(until="2030-01-01T00:00:00Z", prefix="regulated-"):
    return RetentionHold(
        id="hold-1", until=until, applies_to=lambda r: r.id.startswith(prefix), reason="regulatory retention"
    )


def test_check_deletable_blocked_while_hold_is_active():
    record = _make_record()
    blocking = check_deletable(record, [_hold()], current_timestamp="2026-08-23T10:00:00Z")
    assert len(blocking) == 1
    assert blocking[0].id == "hold-1"


def test_check_deletable_allowed_after_hold_expires():
    record = _make_record()
    blocking = check_deletable(record, [_hold(until="2020-01-01T00:00:00Z")], current_timestamp="2026-08-23T10:00:00Z")
    assert blocking == []


def test_check_deletable_ignores_holds_that_dont_apply():
    record = _make_record(record_id="unrelated-001")
    blocking = check_deletable(record, [_hold()], current_timestamp="2026-08-23T10:00:00Z")
    assert blocking == []


def test_enforce_retention_raises_when_blocked():
    record = _make_record()
    with pytest.raises(RetentionViolationError, match="hold-1"):
        enforce_retention(record, [_hold()], current_timestamp="2026-08-23T10:00:00Z")


def test_enforce_retention_passes_when_not_blocked():
    record = _make_record(record_id="unrelated-001")
    assert enforce_retention(record, [_hold()], current_timestamp="2026-08-23T10:00:00Z") is True


def test_enforce_retention_lists_every_blocking_hold():
    record = _make_record()
    holds = [_hold(), _hold()]  # two independent holds both applying
    with pytest.raises(RetentionViolationError) as exc_info:
        enforce_retention(record, holds, current_timestamp="2026-08-23T10:00:00Z")
    assert str(exc_info.value).count("hold-1") == 2

from ledger.record import DecisionRecord, content_hash


def test_content_hash_is_deterministic():
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})


def test_content_hash_differs_for_different_content():
    assert content_hash({"a": 1}) != content_hash({"a": 2})


def _make_record(**overrides):
    fields = dict(
        id="d1",
        timestamp="2026-08-23T10:00:00Z",
        model_version="mv1",
        prompt_version="pv1",
        data_snapshot="ds1",
        input="question",
        output="answer",
        previous_hash="0" * 64,
    )
    fields.update(overrides)
    return DecisionRecord(**fields)


def test_record_hash_changes_when_any_field_changes():
    base = _make_record()
    changed = _make_record(output="a different answer")
    assert base.record_hash() != changed.record_hash()


def test_record_hash_stable_for_identical_records():
    assert _make_record().record_hash() == _make_record().record_hash()


def test_to_dict_from_dict_round_trip():
    record = _make_record()
    restored = DecisionRecord.from_dict(record.to_dict())
    assert restored == record
    assert restored.record_hash() == record.record_hash()


def test_actor_defaults_to_empty_string():
    assert _make_record().actor == ""


def test_record_hash_changes_when_actor_changes():
    base = _make_record()
    attributed = _make_record(actor="service:code-fix-agent")
    assert base.record_hash() != attributed.record_hash()

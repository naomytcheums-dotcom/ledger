import json

import pytest

from ledger.record import DecisionRecord
from ledger.replay import ChainIntegrityError, diff_records, verify_chain
from ledger.store import LedgerStore


def _seeded_store(path):
    store = LedgerStore(path)
    for i in range(3):
        store.append(
            id=f"d{i}",
            timestamp=f"2026-08-23T10:0{i}:00Z",
            model_version="mv1",
            prompt_version="pv1",
            data_snapshot="ds1",
            input=f"question {i}",
            output=f"answer {i}",
        )
    return store


def test_verify_chain_passes_for_intact_chain(tmp_path):
    store = _seeded_store(tmp_path / "ledger.jsonl")
    assert verify_chain(store.read_all()) is True


def _tamper_output(path, index, new_output):
    lines = path.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[index])
    data["output"] = new_output
    lines[index] = json.dumps(data, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_verify_chain_catches_tampering_at_the_next_record(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _seeded_store(path)

    _tamper_output(path, 0, "a forged answer")

    with pytest.raises(ChainIntegrityError, match="record 1"):
        verify_chain(LedgerStore(path).read_all())


def test_verify_chain_cannot_detect_tampering_in_the_most_recent_record(tmp_path):
    """Documents a real, inherent limitation: LedgerStore.append() always
    chains onto whatever the file currently contains. Tamper the last
    record and then keep appending normally, and every new record
    happily chains onto the *tampered* content -- verify_chain never
    breaks, because nothing outside this file remembers what the
    original, untampered hash was. Detecting this class of tampering
    needs an independent checkpoint (the last known-good hash, pinned
    somewhere else) taken before the tampering happened -- this
    library doesn't provide one, so it can't catch this case, and
    pretending otherwise would be worse than documenting it."""
    path = tmp_path / "ledger.jsonl"
    store = _seeded_store(path)

    _tamper_output(path, 2, "a forged final answer")
    assert verify_chain(store.read_all()) is True

    store.append(
        id="d3", timestamp="2026-08-23T10:03:00Z", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="a new question", output="a new answer",
    )
    assert verify_chain(store.read_all()) is True


def test_diff_records_returns_only_changed_fields():
    a = DecisionRecord(
        id="d0", timestamp="t0", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="q", output="answer A", previous_hash="0" * 64,
    )
    b = DecisionRecord(
        id="d0", timestamp="t1", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="q", output="answer B", previous_hash="0" * 64,
    )
    assert diff_records(a, b) == {"output": ("answer A", "answer B")}


def test_diff_records_empty_for_identical_content():
    a = DecisionRecord(
        id="d0", timestamp="t0", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="q", output="a", previous_hash="0" * 64,
    )
    b = DecisionRecord(
        id="d1", timestamp="t1", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="q", output="a", previous_hash="0" * 64,
    )
    assert diff_records(a, b) == {}

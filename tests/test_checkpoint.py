import json

import pytest

from ledger.checkpoint import (
    CheckpointMismatchError,
    create_checkpoint,
    create_merkle_checkpoint,
    load_checkpoint,
    record_inclusion_proof,
    save_checkpoint,
    verify_checkpoint,
    verify_record_inclusion,
)
from ledger.store import LedgerStore


def _seeded_store(path):
    store = LedgerStore(path)
    for i in range(3):
        store.append(
            id=f"d{i}", timestamp=f"2026-08-23T10:0{i}:00Z", model_version="mv1",
            prompt_version="pv1", data_snapshot="ds1", input=f"q{i}", output=f"a{i}",
        )
    return store


def test_create_checkpoint_on_empty_ledger():
    assert create_checkpoint([]) == {"record_count": 0, "head_hash": None}


def test_verify_checkpoint_passes_for_untampered_ledger(tmp_path):
    store = _seeded_store(tmp_path / "ledger.jsonl")
    checkpoint = create_checkpoint(store.read_all())
    assert verify_checkpoint(store.read_all(), checkpoint) is True


def test_verify_checkpoint_catches_tampering_in_the_most_recent_record(tmp_path):
    """This is the exact case verify_chain alone cannot catch --
    tampering the last record, taken *after* an independent checkpoint
    was anchored."""
    path = tmp_path / "ledger.jsonl"
    store = _seeded_store(path)
    checkpoint = create_checkpoint(store.read_all())

    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[-1])
    tampered["output"] = "a forged final answer"
    lines[-1] = json.dumps(tampered, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(CheckpointMismatchError, match="tampering occurred"):
        verify_checkpoint(store.read_all(), checkpoint)


def test_verify_checkpoint_catches_deleted_records(tmp_path):
    path = tmp_path / "ledger.jsonl"
    store = _seeded_store(path)
    checkpoint = create_checkpoint(store.read_all())

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    with pytest.raises(CheckpointMismatchError, match="records were deleted"):
        verify_checkpoint(store.read_all(), checkpoint)


def test_checkpoint_round_trips_through_a_file(tmp_path):
    store = _seeded_store(tmp_path / "ledger.jsonl")
    checkpoint = create_checkpoint(store.read_all())
    checkpoint_path = tmp_path / "checkpoint.json"

    save_checkpoint(checkpoint_path, checkpoint)
    loaded = load_checkpoint(checkpoint_path)

    assert loaded == checkpoint


def test_verify_record_inclusion_true_for_a_real_member(tmp_path):
    store = _seeded_store(tmp_path / "ledger.jsonl")
    records = store.read_all()
    checkpoint = create_merkle_checkpoint(records)

    proof = record_inclusion_proof(records, 1)

    assert verify_record_inclusion(records[1], proof, checkpoint) is True


def test_verify_record_inclusion_false_for_a_tampered_record(tmp_path):
    store = _seeded_store(tmp_path / "ledger.jsonl")
    records = store.read_all()
    checkpoint = create_merkle_checkpoint(records)
    proof = record_inclusion_proof(records, 1)

    from dataclasses import replace

    forged = replace(records[1], output="a forged answer")

    assert verify_record_inclusion(forged, proof, checkpoint) is False


def test_record_inclusion_does_not_require_the_rest_of_the_ledger(tmp_path):
    """The whole point of the Merkle checkpoint: verifying one record
    needs only that record and its proof, not every other record."""
    store = _seeded_store(tmp_path / "ledger.jsonl")
    records = store.read_all()
    checkpoint = create_merkle_checkpoint(records)
    proof = record_inclusion_proof(records, 2)
    the_one_record = records[2]

    del records  # simulate the verifier never having had the rest of the ledger

    assert verify_record_inclusion(the_one_record, proof, checkpoint) is True

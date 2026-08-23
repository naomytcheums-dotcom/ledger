from ledger.record import GENESIS_HASH
from ledger.store import LedgerStore


def _append_three(store):
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


def test_append_chains_previous_hash(tmp_path):
    store = LedgerStore(tmp_path / "ledger.jsonl")
    first = store.append(
        id="d0", timestamp="t0", model_version="mv", prompt_version="pv", data_snapshot="ds", input="q", output="a"
    )
    assert first.previous_hash == GENESIS_HASH

    second = store.append(
        id="d1", timestamp="t1", model_version="mv", prompt_version="pv", data_snapshot="ds", input="q2", output="a2"
    )
    assert second.previous_hash == first.record_hash()


def test_read_all_returns_records_in_order(tmp_path):
    store = LedgerStore(tmp_path / "ledger.jsonl")
    _append_three(store)
    records = store.read_all()
    assert [r.id for r in records] == ["d0", "d1", "d2"]


def test_read_all_on_missing_file_returns_empty_list(tmp_path):
    store = LedgerStore(tmp_path / "does_not_exist.jsonl")
    assert store.read_all() == []


def test_persists_across_store_instances(tmp_path):
    path = tmp_path / "ledger.jsonl"
    LedgerStore(path).append(
        id="d0", timestamp="t0", model_version="mv", prompt_version="pv", data_snapshot="ds", input="q", output="a"
    )
    reopened = LedgerStore(path)
    assert [r.id for r in reopened.read_all()] == ["d0"]

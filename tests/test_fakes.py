from ledger.fakes import InMemoryLedgerStore
from ledger.record import GENESIS_HASH
from ledger.replay import verify_chain


def test_in_memory_store_chains_like_the_real_store():
    store = InMemoryLedgerStore()
    first = store.append(
        id="d0", timestamp="t0", model_version="mv", prompt_version="pv", data_snapshot="ds", input="q", output="a"
    )
    assert first.previous_hash == GENESIS_HASH

    second = store.append(
        id="d1", timestamp="t1", model_version="mv", prompt_version="pv", data_snapshot="ds", input="q2", output="a2"
    )
    assert second.previous_hash == first.record_hash()


def test_in_memory_store_read_all_verifies_as_a_valid_chain():
    store = InMemoryLedgerStore()
    for i in range(4):
        store.append(
            id=f"d{i}", timestamp=f"t{i}", model_version="mv", prompt_version="pv",
            data_snapshot="ds", input=f"q{i}", output=f"a{i}",
        )
    assert verify_chain(store.read_all()) is True


def test_in_memory_store_read_all_returns_a_copy():
    store = InMemoryLedgerStore()
    store.append(
        id="d0", timestamp="t0", model_version="mv", prompt_version="pv", data_snapshot="ds", input="q", output="a"
    )
    records = store.read_all()
    records.clear()
    assert len(store.read_all()) == 1

from ledger.fakes import InMemoryLedgerStore
from ledger.query import between, by_data_snapshot, by_model_version, by_prompt_version


def _seeded_store():
    store = InMemoryLedgerStore()
    store.append(
        id="d0", timestamp="2026-08-23T10:00:00Z", model_version="mv1",
        prompt_version="pv1", data_snapshot="ds1", input="q0", output="a0",
    )
    store.append(
        id="d1", timestamp="2026-08-23T11:00:00Z", model_version="mv2",
        prompt_version="pv1", data_snapshot="ds2", input="q1", output="a1",
    )
    store.append(
        id="d2", timestamp="2026-08-23T12:00:00Z", model_version="mv1",
        prompt_version="pv2", data_snapshot="ds1", input="q2", output="a2",
    )
    return store


def test_by_prompt_version_filters_correctly():
    records = _seeded_store().read_all()
    assert [r.id for r in by_prompt_version(records, "pv1")] == ["d0", "d1"]


def test_by_model_version_filters_correctly():
    records = _seeded_store().read_all()
    assert [r.id for r in by_model_version(records, "mv1")] == ["d0", "d2"]


def test_by_data_snapshot_filters_correctly():
    records = _seeded_store().read_all()
    assert [r.id for r in by_data_snapshot(records, "ds1")] == ["d0", "d2"]


def test_between_is_inclusive_of_range_boundaries():
    records = _seeded_store().read_all()
    result = between(records, "2026-08-23T10:00:00Z", "2026-08-23T11:00:00Z")
    assert [r.id for r in result] == ["d0", "d1"]

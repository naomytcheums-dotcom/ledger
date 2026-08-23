import json

from ledger.checkpoint import create_checkpoint, save_checkpoint
from ledger.cli import main
from ledger.store import LedgerStore


def _seeded_ledger(path):
    store = LedgerStore(path)
    for i in range(3):
        store.append(
            id=f"d{i}", timestamp=f"2026-08-23T10:0{i}:00Z", model_version="mv1",
            prompt_version="pv1", data_snapshot="ds1", input=f"question {i}",
            output=f"answer {i}", actor="service:a" if i % 2 == 0 else "service:b",
        )
    return store


def test_verify_ok(tmp_path, capsys):
    path = tmp_path / "ledger.jsonl"
    _seeded_ledger(path)

    exit_code = main(["verify", str(path)])

    assert exit_code == 0
    assert "OK: 3 records" in capsys.readouterr().out


def test_verify_empty_ledger(tmp_path, capsys):
    exit_code = main(["verify", str(tmp_path / "missing.jsonl")])
    assert exit_code == 0
    assert "empty ledger" in capsys.readouterr().out


def test_verify_detects_tampering(tmp_path, capsys):
    path = tmp_path / "ledger.jsonl"
    _seeded_ledger(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[0])
    data["output"] = "forged"
    lines[0] = json.dumps(data, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    exit_code = main(["verify", str(path)])

    assert exit_code == 1
    assert "FAILED" in capsys.readouterr().err


def test_checkpoint_create_and_verify_round_trip(tmp_path, capsys):
    ledger_path = tmp_path / "ledger.jsonl"
    checkpoint_path = tmp_path / "checkpoint.json"
    _seeded_ledger(ledger_path)

    create_exit = main(["checkpoint", "create", str(ledger_path), str(checkpoint_path)])
    assert create_exit == 0
    assert checkpoint_path.exists()

    verify_exit = main(["checkpoint", "verify", str(ledger_path), str(checkpoint_path)])
    assert verify_exit == 0
    assert "OK: ledger matches checkpoint" in capsys.readouterr().out


def test_checkpoint_verify_detects_mismatch(tmp_path, capsys):
    ledger_path = tmp_path / "ledger.jsonl"
    checkpoint_path = tmp_path / "checkpoint.json"
    store = _seeded_ledger(ledger_path)
    save_checkpoint(checkpoint_path, create_checkpoint(store.read_all()))

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[-1])
    data["output"] = "forged"
    lines[-1] = json.dumps(data, sort_keys=True)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    exit_code = main(["checkpoint", "verify", str(ledger_path), str(checkpoint_path)])

    assert exit_code == 1
    assert "FAILED" in capsys.readouterr().err


def test_query_filters_by_actor(tmp_path, capsys):
    path = tmp_path / "ledger.jsonl"
    _seeded_ledger(path)

    main(["query", str(path), "--actor", "service:a"])

    out = capsys.readouterr().out
    assert "2 matching record(s)" in out
    assert "d0" in out and "d2" in out
    assert "d1" not in out


def test_query_with_no_filters_returns_all(tmp_path, capsys):
    path = tmp_path / "ledger.jsonl"
    _seeded_ledger(path)

    main(["query", str(path)])

    assert "3 matching record(s)" in capsys.readouterr().out

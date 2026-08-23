"""
Seeds a small ledger with a few decisions (modeled on the
question-answering agent from rag-fastapi-assistant), verifies the
chain is intact, then tampers with a record directly in the file --
the way a bug or a bad actor would, not through this library's own
API -- and shows verify_chain() catching exactly where the chain
breaks.

Run: python demo.py
"""

import json
from pathlib import Path

from ledger import ChainIntegrityError, LedgerStore, data_snapshot, model_version, prompt_version, verify_chain

LEDGER_PATH = Path(__file__).parent / "demo_ledger.jsonl"

PROMPT = "Answer the user's question about the FastAPI documentation, citing sources."


def seed():
    if LEDGER_PATH.exists():
        LEDGER_PATH.unlink()

    store = LedgerStore(LEDGER_PATH)
    mv = model_version("claude-sonnet-5")
    pv = prompt_version(PROMPT)
    snapshot = data_snapshot({"docs_version": "v1.2"})

    questions = [
        "How do I add a path parameter?",
        "Does the framework support server-sent events?",
        "What's the difference between Depends and Security?",
    ]
    for i, question in enumerate(questions):
        store.append(
            id=f"decision-{i}",
            timestamp=f"2026-08-23T10:0{i}:00Z",
            model_version=mv,
            prompt_version=pv,
            data_snapshot=snapshot,
            input=question,
            output=f"[answer to: {question}]",
        )
    return store


def main():
    store = seed()
    records = store.read_all()
    print(f"Seeded {len(records)} decisions to {LEDGER_PATH.name}")

    verify_chain(records)
    print("Chain verified: every record's hash links correctly to the one before it.")

    print("\nTampering with the second record's output directly in the file (not through the library API)...")
    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[1])
    tampered["output"] = "[a different answer nobody actually approved]"
    lines[1] = json.dumps(tampered, sort_keys=True)
    LEDGER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tampered_records = store.read_all()
    try:
        verify_chain(tampered_records)
        print("Chain still verified -- this should not happen.")
    except ChainIntegrityError as exc:
        print(f"Tampering caught: {exc}")


if __name__ == "__main__":
    main()

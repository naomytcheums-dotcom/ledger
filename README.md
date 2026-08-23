# ledger

[![Tests](https://github.com/naomytcheums-dotcom/ledger/actions/workflows/tests.yml/badge.svg)](https://github.com/naomytcheums-dotcom/ledger/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A tamper-evident audit trail for AI/agent decisions — which model,
which prompt, which input data produced a given output, hash-chained
so altering or deleting a past record breaks every hash after it.

## Where this came from

A regulated AI deployment shipped a technically correct recommendation
with no way to answer a simple question afterward: which data version,
which model, which prompt actually produced it. The fix wasn't a
smarter model — it was making the audit trail come first and the
model's cleverness second. `ledger` is that principle as a small,
dependency-free library instead of a one-off fix: a chained log of
*what produced this decision*, verifiable after the fact.

## Install

```bash
pip install ledger
```

(Not yet published to PyPI — for now, install from source: `pip install -e .` after cloning.)

## The six pieces

### 1. Content-addressed versioning — "version 3" always means the same bytes

```python
from ledger import model_version, prompt_version, data_snapshot

mv = model_version("claude-sonnet-5", {"temperature": 0})
pv = prompt_version("Answer the user's question, citing sources.")
ds = data_snapshot({"docs_version": "v1.2"})
# same inputs -> same id, anywhere, anytime -- no manually incremented version numbers to drift
```

### 2. Append a decision to the ledger

```python
from ledger import LedgerStore

store = LedgerStore("decisions.jsonl")
store.append(
    id="decision-042", timestamp="2026-08-23T10:00:00Z",
    model_version=mv, prompt_version=pv, data_snapshot=ds,
    input="How do I add a path parameter?", output="...",
)
```

### 3. Verify the chain is actually intact

```python
from ledger import verify_chain, ChainIntegrityError

try:
    verify_chain(store.read_all())
except ChainIntegrityError as exc:
    print(f"Someone altered the ledger: {exc}")
```

### 4. Audit queries

```python
from ledger import by_prompt_version, between

records = store.read_all()
by_prompt_version(records, pv)  # every decision made under this exact prompt
between(records, "2026-08-23T00:00:00Z", "2026-08-23T23:59:59Z")  # a day's decisions
```

### 5. Diff two records of "the same" decision re-run later

```python
from ledger import diff_records

diff_records(old_record, new_record)
# {"model_version": ("mv1", "mv2")} -- only the model changed; prompt and data didn't
```

### 6. Test pipeline code without touching disk

```python
from ledger import InMemoryLedgerStore

store = InMemoryLedgerStore()  # same append()/read_all() shape as LedgerStore, no file
```

## The demo catches real tampering

`demo.py` seeds a small ledger, verifies it, then edits one record's
output directly in the file — not through the library's own API, the
way a bug or a bad actor actually would — and shows `verify_chain()`
catching it:

```bash
python demo.py
```

```
Seeded 3 decisions to demo_ledger.jsonl
Chain verified: every record's hash links correctly to the one before it.

Tampering with the second record's output directly in the file (not through the library API)...
Tampering caught: record 2 (id='decision-2') has previous_hash '4b1b0f07...', expected 'ed992e93...'
-- a record before it was altered, inserted, or deleted
```

Notice the break is reported at record 2, not the tampered record 1 —
that's not a bug. See Known limitations.

## Known limitations

- **Tampering with the most recent record, followed by normal appends, is not detectable.** `LedgerStore.append()`
  always chains onto whatever the file currently contains. If the last record is edited and then more decisions
  are appended normally, every new record happily chains onto the *tampered* content — `verify_chain()` never
  breaks, because nothing outside the file remembers the original hash. This is tested explicitly
  (`test_verify_chain_cannot_detect_tampering_in_the_most_recent_record`), not just claimed. Catching this case
  needs an independent checkpoint of the last known-good hash taken *before* the tampering — publish it to a
  second system, print it to a build log, anything outside the file itself. This library doesn't provide one.
- **A break is reported at the record *after* the tampered one, not the tampered one itself.** A record's own
  `previous_hash` field points backward and isn't affected by changes to its own content — only the hash it
  produces going forward changes. Same reason a blockchain or a chain of git commits works this way.
- **No encryption, no access control.** This is tamper-*evidence*, not tamper-*prevention* — anyone with file
  access can still edit it, they just can't do so undetected (subject to the limitation above).

## Tests

```bash
pytest tests/ -v
```

26 tests, all offline. Unlike the rest of this portfolio, nothing here needs a live LLM call to be fully
exercised — this library records and verifies metadata about a decision that already happened, so every module
is tested end-to-end with no funded API key required.

## Where this fits in the portfolio

Extends the tracing already built for
[llm-observatory](https://github.com/naomytcheums-dotcom/llm-observatory) (cost, latency, guardrails) with the
one piece that project doesn't cover: proving *what produced* a decision, and that the record of it wasn't
altered afterward.

## Status

Early (`v0.1.0`, alpha). All six modules are complete and tested, and the tamper-detection demo runs end-to-end.
Not yet published to PyPI. Feedback and issues welcome.

## License

MIT

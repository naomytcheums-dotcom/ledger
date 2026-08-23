# ledger

[![Tests](https://github.com/naomytcheums-dotcom/ledger/actions/workflows/tests.yml/badge.svg)](https://github.com/naomytcheums-dotcom/ledger/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[Live dashboard →](https://ledger-ijwocha8temkjeq7unuxuh.streamlit.app/)** — click "Load demo data" in the sidebar, no setup required.

A tamper-evident audit trail for AI/agent decisions — which model,
which prompt, which input data produced a given output, hash-chained
so altering or deleting a past record breaks every hash after it.
Compliance-*support* primitives, not a certified compliance product
(see [Known limitations](#known-limitations) for the honest line
between the two).

`v0.3.0` adds a CLI, Merkle-tree checkpoints (verify one record's
inclusion without reading the whole ledger), public-key signing, and a
Streamlit dashboard for browsing a ledger visually.

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
Optional extras: `pip install ledger[pki]` for public-key signing, `pip install ledger[dashboard]` for the
Streamlit viewer.

## The thirteen pieces

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

### 7. Checkpoint the chain externally — closes the "most recent record" gap

```python
from ledger import create_checkpoint, verify_checkpoint

checkpoint = create_checkpoint(store.read_all())
# store this SOMEWHERE ELSE -- a second system, a build log, a git commit -- not back in the same file

verify_checkpoint(store.read_all(), checkpoint)  # raises CheckpointMismatchError if anything since changed
```

### 8. Sign a record — proves it was written by a holder of a given key

```python
from ledger import sign_record, verify_signature

signature = sign_record(record, secret="per-service-secret")
verify_signature(record, signature, secret="per-service-secret")  # False if the record or the key don't match
```

### 9. Enforce retention holds before deleting anything

```python
from ledger import RetentionHold, enforce_retention

hold = RetentionHold(
    id="fda-2026-audit", until="2031-01-01T00:00:00Z",
    applies_to=lambda r: r.id.startswith("clinical-"), reason="regulatory retention",
)
enforce_retention(record, holds=[hold], current_timestamp=now)  # raises RetentionViolationError if blocked
```

### 10. Verify the chain, a checkpoint, or run a query without writing Python

```bash
ledger verify decisions.jsonl
ledger checkpoint create decisions.jsonl checkpoint.json
ledger checkpoint verify decisions.jsonl checkpoint.json
ledger query decisions.jsonl --actor "service:rag-fastapi-assistant" --since 2026-08-01T00:00:00Z
```

### 11. Prove one record's inclusion without reading the whole ledger

A plain checkpoint (piece 7) proves the *whole chain* up to a point is
what it was — checking it still needs every record. A Merkle checkpoint
lets a verifier check *one* record with only a small proof:

```python
from ledger import checkpoint  # create_merkle_checkpoint, record_inclusion_proof, verify_record_inclusion

records = store.read_all()
mc = checkpoint.create_merkle_checkpoint(records)          # {"record_count", "merkle_root"} -- publish this
proof = checkpoint.record_inclusion_proof(records, index=42)  # hand this + the one record to a verifier

# the verifier needs only `records[42]`, `proof`, and `mc` -- not the other 10,000 records
checkpoint.verify_record_inclusion(records[42], proof, mc)  # True
```

### 12. Sign with a real keypair instead of a shared secret

```python
from ledger.pki import generate_keypair, sign_record, verify_signature  # needs: pip install ledger[pki]

private_key, public_key = generate_keypair()  # one keypair per actor -- private key never leaves them
signature = sign_record(record, private_key)
verify_signature(record, signature, public_key)  # anyone with the public key can check this, nobody can forge it
```

### 13. Browse and verify a ledger visually

**[Try it live →](https://ledger-ijwocha8temkjeq7unuxuh.streamlit.app/)** (deployed on Streamlit Community Cloud) or run it yourself:

```bash
pip install ledger[dashboard]
streamlit run dashboard/app.py
```

Shows record count, chain status, distinct actors/prompt versions, an optional checkpoint check, and a
filterable table — deliberately uncached, since a stale "verified" status in a tamper-evidence viewer would be
actively misleading.

## The demo catches real tampering

`demo.py` seeds a small ledger, verifies it, then edits a record's
output directly in the file — not through the library's own API, the
way a bug or a bad actor actually would — twice: once mid-chain (which
`verify_chain()` alone catches), once on the very last record (which it
structurally can't, and `verify_checkpoint()` catches instead):

```bash
python demo.py
```

```
Seeded 3 decisions to demo_ledger.jsonl
Chain verified: every record's hash links correctly to the one before it.

Tampering with the second record's output directly in the file (not through the library API)...
Tampering caught: record 2 (id='decision-2') has previous_hash 'd1cb8f99...', expected 'cbb2dfa2...'
-- a record before it was altered, inserted, or deleted

--- Now the case verify_chain alone can't catch: tampering the LAST record ---
Checkpoint taken and stored externally: {'record_count': 3, 'head_hash': 'd6264ba3...'}
verify_chain() alone still reports True: True -- it genuinely can't see this.
But verify_checkpoint() catches it: checkpoint recorded head_hash 'd6264ba3...' at record 3,
but the ledger now computes '8384f705...' there -- tampering occurred after the checkpoint was taken
```

## Known limitations

- **A break from `verify_chain` is reported at the record *after* the tampered one, not the tampered one
  itself.** A record's own `previous_hash` field points backward and isn't affected by changes to its own
  content — only the hash it produces going forward changes. Same reason a blockchain or a chain of git commits
  works this way.
- **Checkpointing only helps if it's actually used.** `verify_checkpoint` closes the "tamper the most recent
  record" gap *only* for records written before a checkpoint was taken and stored somewhere independent of the
  ledger file. Nothing enforces that discipline — skip taking checkpoints, or store one next to the ledger file
  it's meant to audit, and the gap reopens exactly as documented and tested in `test_verify_chain_cannot_detect_tampering_in_the_most_recent_record`.
- **Signing proves a key, not a person.** `verify_signature` proves a record was produced by *someone holding
  that secret* — it says nothing about which specific person or process that was unless you already run strict
  one-key-per-actor discipline and protect key distribution separately. This library has no key management.
- **Retention is advisory, not enforced by the storage layer.** `enforce_retention` raises if a hold applies —
  but nothing stops a caller from deleting the underlying file directly and skipping the check entirely. It's a
  policy gate for code that calls it, not a database-level guarantee.
- **No encryption, no access control on the file itself.** This is tamper-*evidence*, not tamper-*prevention* —
  anyone with file access can still edit it; the point is that they can't do so undetected, subject to the
  limitations above.
- **Not a certified compliance product.** These are real, tested primitives toward regulatory readiness — not a
  replacement for organizational validation, documented procedures, or legal review, none of which a library can
  provide by itself.
- **PKI signing still proves a keypair, not a person, without your own key-issuance process.** `ledger.pki` gets
  you real per-actor identity *if* you issue one keypair per actor and protect private key distribution — it
  doesn't do that issuance for you.
- **The Merkle checkpoint (piece 11) needs the full record list to *produce* a proof, only to *verify* one.**
  Generating `record_inclusion_proof` still requires every record's hash at checkpoint time; the savings are on
  the verifier's side, who afterward needs only the one record and its proof.

## Tests

```bash
pytest tests/ -v
```

78 tests, all offline. Unlike the rest of this portfolio, nothing here needs a live LLM call to be fully
exercised — this library records and verifies metadata about a decision that already happened, so every module
is tested end-to-end with no funded API key required. `pki` tests need the optional `cryptography` dependency
(`pip install ledger[dev,pki]`); CI installs it.

## Where this fits in the portfolio

Extends the tracing already built for
[llm-observatory](https://github.com/naomytcheums-dotcom/llm-observatory) (cost, latency, guardrails) with the
one piece that project doesn't cover: proving *what produced* a decision, and that the record of it wasn't
altered afterward.

## Status

Early (`v0.3.0`, alpha). All thirteen pieces are complete and tested, the tamper-detection demo runs end-to-end
for both the mid-chain and most-recent-record cases, the CLI is installed and smoke-tested as a real entry
point, and the dashboard has been run and verified in a browser. Not yet published to PyPI. Feedback and issues
welcome.

## License

MIT

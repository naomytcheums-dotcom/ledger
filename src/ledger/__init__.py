"""
ledger -- a tamper-evident audit trail for AI/agent decisions: which
model, which prompt, which input data produced a given output, chained
so that altering or deleting a past record breaks every hash after it.

Built after a real conversation about a real mistake in a regulated
AI deployment: a technically correct recommendation shipped without an
audit trail, caught only because a regulatory reviewer asked "which
data version produced this?" and nobody could answer. The fix was
making the audit trail come first and the model's cleverness second.
ledger is that principle as a small, dependency-free library.

These are compliance-*support* primitives, not a certified compliance
product -- checkpointing, signing, and retention enforcement are real,
tested building blocks toward regulatory readiness (CFR Part 11-style
requirements included), but full compliance also needs organizational
validation and legal review that no library can provide by itself.

Nine pieces:
- `record`     -- DecisionRecord: one decision, fully attributed
                  (including an optional `actor`), with its own
                  tamper-evidence hash.
- `versioning` -- content-addressed ids for a prompt, a model, or an
                  input data snapshot, so "version 3" always means the
                  same bytes.
- `store`      -- an append-only, hash-chained ledger backed by a JSONL
                  file.
- `replay`     -- verify a ledger's hash chain is actually intact, and
                  diff two records claiming to represent the same
                  decision at different times.
- `query`      -- audit queries over a loaded ledger: by prompt
                  version, model version, data snapshot, actor, or time
                  range.
- `checkpoint` -- an externally anchored snapshot of the chain's head,
                  closing the one gap `replay.verify_chain` alone can't:
                  tampering in the single most recent record.
- `signing`    -- HMAC-based record signing, proving a record was
                  produced by a holder of a given key.
- `retention`  -- retention holds that block deleting a record before
                  its policy window ends.
- `fakes`      -- an in-memory ledger store for testing pipeline code
                  without touching disk.

Unlike the rest of this portfolio, nothing here needs a live LLM call
to be fully exercised: it records and verifies metadata about a
decision that already happened, so every module is tested end-to-end,
no funded API key required.
"""

from ledger.checkpoint import CheckpointMismatchError, create_checkpoint, load_checkpoint, save_checkpoint, verify_checkpoint
from ledger.fakes import InMemoryLedgerStore
from ledger.query import between, by_actor, by_data_snapshot, by_model_version, by_prompt_version
from ledger.record import DecisionRecord, GENESIS_HASH, content_hash
from ledger.replay import ChainIntegrityError, diff_records, verify_chain
from ledger.retention import RetentionHold, RetentionViolationError, check_deletable, enforce_retention
from ledger.signing import sign_record, verify_signature
from ledger.store import LedgerStore
from ledger.versioning import data_snapshot, model_version, prompt_version

__all__ = [
    "DecisionRecord",
    "GENESIS_HASH",
    "content_hash",
    "prompt_version",
    "model_version",
    "data_snapshot",
    "LedgerStore",
    "ChainIntegrityError",
    "verify_chain",
    "diff_records",
    "by_prompt_version",
    "by_model_version",
    "by_data_snapshot",
    "by_actor",
    "between",
    "CheckpointMismatchError",
    "create_checkpoint",
    "verify_checkpoint",
    "save_checkpoint",
    "load_checkpoint",
    "sign_record",
    "verify_signature",
    "RetentionHold",
    "RetentionViolationError",
    "check_deletable",
    "enforce_retention",
    "InMemoryLedgerStore",
]

__version__ = "0.2.0"

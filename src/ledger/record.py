"""
A single traced AI/agent decision -- what produced it, not just what
it said. Every field answers a question an auditor would ask after the
fact: which model, which prompt, which input data, and can this record
be proven unmodified since it was written.
"""

import hashlib
import json
from dataclasses import dataclass

GENESIS_HASH = "0" * 64


def content_hash(value):
    """A deterministic hex digest of any JSON-serializable value --
    used both for content-addressed version ids and for a record's own
    tamper-evidence hash. Same content, same hash, regardless of when
    or where it's computed."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DecisionRecord:
    """One decision, fully attributed. `model_version` and
    `prompt_version` are content-hash ids (see `versioning.py`) rather
    than manually incremented numbers, so two records referencing "the
    same" prompt are provably referencing byte-identical text.
    `previous_hash` links this record to the one before it in the
    ledger -- the chain that makes tampering detectable."""

    id: str
    timestamp: str
    model_version: str
    prompt_version: str
    data_snapshot: str
    input: str
    output: str
    previous_hash: str

    def record_hash(self):
        """This record's own content hash, including `previous_hash` --
        the link in the chain. Change any field, even by one
        character, and this hash changes."""
        return content_hash(
            {
                "id": self.id,
                "timestamp": self.timestamp,
                "model_version": self.model_version,
                "prompt_version": self.prompt_version,
                "data_snapshot": self.data_snapshot,
                "input": self.input,
                "output": self.output,
                "previous_hash": self.previous_hash,
            }
        )

    def to_dict(self):
        d = dict(self.__dict__)
        d["record_hash"] = self.record_hash()
        return d

    @classmethod
    def from_dict(cls, data):
        """`record_hash` is dropped and recomputed, never trusted from
        the file -- a stored hash that simply lies about a tampered
        record would defeat the entire point of this module."""
        fields = {k: v for k, v in data.items() if k != "record_hash"}
        return cls(**fields)

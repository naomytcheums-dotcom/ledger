"""
Periodic external checkpoints of the ledger's current chain head --
closes the one real gap documented in `replay.py`: a hash chain proves
nothing about its own newest entries until an independent, externally
anchored record exists to compare against. A checkpoint is that
anchor.
"""

import json

from ledger.merkle import merkle_proof, merkle_root, verify_merkle_proof


class CheckpointMismatchError(ValueError):
    """Raised by `verify_checkpoint` -- proof that something in the
    checkpointed range was altered after the checkpoint was taken, the
    exact class of tampering `verify_chain` alone can't see."""


def create_checkpoint(records):
    """A checkpoint is just the position and hash of the chain's head
    at the moment it's taken. Meant to be stored somewhere *other* than
    the ledger file itself -- a separate checkpoint log, a build log, a
    git commit, a second system -- anchoring it in the same file it's
    meant to audit would defeat the point."""
    if not records:
        return {"record_count": 0, "head_hash": None}
    return {"record_count": len(records), "head_hash": records[-1].record_hash()}


def verify_checkpoint(records, checkpoint):
    """Recomputes the head hash at the checkpointed position and
    compares it against what was anchored. Unlike `verify_chain` alone,
    this can catch tampering in the single most recent record, as long
    as a checkpoint was taken after it and stored independently of the
    ledger file."""
    count = checkpoint["record_count"]
    if count == 0:
        return True
    if len(records) < count:
        raise CheckpointMismatchError(
            f"checkpoint expects at least {count} records, ledger now has {len(records)} -- records were deleted"
        )
    actual_hash = records[count - 1].record_hash()
    if actual_hash != checkpoint["head_hash"]:
        raise CheckpointMismatchError(
            f"checkpoint recorded head_hash {checkpoint['head_hash']!r} at record {count}, "
            f"but the ledger now computes {actual_hash!r} there -- tampering occurred after the checkpoint was taken"
        )
    return True


def save_checkpoint(path, checkpoint):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)


def load_checkpoint(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_merkle_checkpoint(records):
    """Like `create_checkpoint`, but commits to every record's hash via
    a Merkle root instead of just the chain head. The point isn't
    stronger tamper-evidence than the plain checkpoint -- it's that a
    verifier can later check *one* record's inclusion (see
    `verify_record_inclusion`) without needing the rest of the ledger
    at all, which the plain checkpoint can't offer."""
    leaf_hashes = [r.record_hash() for r in records]
    return {"record_count": len(records), "merkle_root": merkle_root(leaf_hashes)}


def record_inclusion_proof(records, index):
    """The Merkle proof for `records[index]` against
    `create_merkle_checkpoint(records)`'s root. Computed here (with the
    full ledger available) so it can be handed to a verifier who has
    only the one record and this proof -- not the rest of the ledger."""
    leaf_hashes = [r.record_hash() for r in records]
    return merkle_proof(leaf_hashes, index)


def verify_record_inclusion(record, proof, merkle_checkpoint):
    """True iff `record` is proven included in the tree committed to
    by `merkle_checkpoint["merkle_root"]`, using only `record` and
    `proof` -- no other records needed."""
    return verify_merkle_proof(record.record_hash(), proof, merkle_checkpoint["merkle_root"])

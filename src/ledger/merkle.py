"""
A Merkle tree over ledger record hashes -- lets a checkpoint prove one
record's inclusion with O(log n) sibling hashes, instead of requiring
every record to be re-read and re-hashed. Complements checkpoint.py's
simple head-hash checkpoint: that proves "the whole chain up to here is
what it was," this proves "this one specific record is definitely in
there" without needing the rest of the ledger to check it.
"""

from ledger.record import content_hash


def _hash_pair(left, right):
    return content_hash({"left": left, "right": right})


def merkle_root(leaf_hashes):
    """Bottom-up Merkle root: pair up hashes, hash each pair, repeat.
    An odd leaf out at any level is paired with itself rather than left
    unhashed -- a common, simple convention. Returns None for an empty
    list; the single-leaf case returns that leaf's hash unchanged."""
    if not leaf_hashes:
        return None
    level = list(leaf_hashes)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            next_level.append(_hash_pair(left, right))
        level = next_level
    return level[0]


def merkle_proof(leaf_hashes, index):
    """The sibling hash at each level needed to recompute the root
    starting from `leaf_hashes[index]` alone -- a list of
    `(side, hash)` pairs, `side` being which side of the pair the
    sibling sits on ("left" or "right") relative to the node on the
    path being proven."""
    if not (0 <= index < len(leaf_hashes)):
        raise IndexError(f"index {index} out of range for {len(leaf_hashes)} leaves")

    proof = []
    level = list(leaf_hashes)
    pos = index
    while len(level) > 1:
        next_level = []
        next_pos = None
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            if i == pos:
                proof.append(("right", right))
                next_pos = len(next_level)
            elif i + 1 == pos:
                proof.append(("left", left))
                next_pos = len(next_level)
            next_level.append(_hash_pair(left, right))
        level = next_level
        pos = next_pos
    return proof


def verify_merkle_proof(leaf_hash, proof, root):
    """Recomputes the root from `leaf_hash` and `proof` alone -- no
    access to any other leaf required. Returns True iff the result
    matches `root`."""
    current = leaf_hash
    for side, sibling in proof:
        current = _hash_pair(current, sibling) if side == "right" else _hash_pair(sibling, current)
    return current == root

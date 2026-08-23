import pytest

from ledger.merkle import merkle_proof, merkle_root, verify_merkle_proof


def test_merkle_root_empty_is_none():
    assert merkle_root([]) is None


def test_merkle_root_single_leaf_is_the_leaf_itself():
    assert merkle_root(["h0"]) == "h0"


def test_merkle_root_is_deterministic():
    leaves = ["h0", "h1", "h2", "h3"]
    assert merkle_root(leaves) == merkle_root(list(leaves))


def test_merkle_root_changes_if_any_leaf_changes():
    base = merkle_root(["h0", "h1", "h2", "h3"])
    changed = merkle_root(["h0", "h1", "h2", "different"])
    assert base != changed


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 7, 8, 13])
def test_every_leaf_proof_verifies_against_the_root(size):
    leaves = [f"leaf-{i}" for i in range(size)]
    root = merkle_root(leaves)
    for index in range(size):
        proof = merkle_proof(leaves, index)
        assert verify_merkle_proof(leaves[index], proof, root) is True


def test_proof_fails_for_a_different_leaf_value():
    leaves = [f"leaf-{i}" for i in range(5)]
    root = merkle_root(leaves)
    proof = merkle_proof(leaves, 2)
    assert verify_merkle_proof("a-forged-leaf", proof, root) is False


def test_proof_fails_against_a_different_root():
    leaves = [f"leaf-{i}" for i in range(5)]
    proof = merkle_proof(leaves, 2)
    assert verify_merkle_proof(leaves[2], proof, "some-other-root") is False


def test_merkle_proof_rejects_out_of_range_index():
    with pytest.raises(IndexError):
        merkle_proof(["h0", "h1"], 5)

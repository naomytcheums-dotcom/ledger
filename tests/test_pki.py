from ledger.pki import (
    generate_keypair,
    private_key_from_pem,
    private_key_to_pem,
    public_key_from_pem,
    public_key_to_pem,
    sign_record,
    verify_signature,
)
from ledger.record import DecisionRecord


def _make_record(**overrides):
    fields = dict(
        id="d1", timestamp="t0", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="question", output="answer", previous_hash="0" * 64,
    )
    fields.update(overrides)
    return DecisionRecord(**fields)


def test_sign_and_verify_round_trip():
    private_key, public_key = generate_keypair()
    record = _make_record()

    signature = sign_record(record, private_key)

    assert verify_signature(record, signature, public_key) is True


def test_verify_fails_for_the_wrong_public_key():
    private_key, _ = generate_keypair()
    _, other_public_key = generate_keypair()
    record = _make_record()

    signature = sign_record(record, private_key)

    assert verify_signature(record, signature, other_public_key) is False


def test_verify_fails_after_tampering_with_the_record():
    private_key, public_key = generate_keypair()
    record = _make_record()
    signature = sign_record(record, private_key)

    tampered = _make_record(output="a forged answer")

    assert verify_signature(tampered, signature, public_key) is False


def test_two_generated_keypairs_are_different():
    private_a, public_a = generate_keypair()
    private_b, public_b = generate_keypair()
    record = _make_record()

    signature_a = sign_record(record, private_a)

    assert verify_signature(record, signature_a, public_b) is False


def test_private_key_pem_round_trip_preserves_signing():
    private_key, public_key = generate_keypair()
    record = _make_record()

    pem = private_key_to_pem(private_key)
    restored_private_key = private_key_from_pem(pem)
    signature = sign_record(record, restored_private_key)

    assert verify_signature(record, signature, public_key) is True


def test_public_key_pem_round_trip_preserves_verification():
    private_key, public_key = generate_keypair()
    record = _make_record()
    signature = sign_record(record, private_key)

    pem = public_key_to_pem(public_key)
    restored_public_key = public_key_from_pem(pem)

    assert verify_signature(record, signature, restored_public_key) is True

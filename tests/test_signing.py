from ledger.record import DecisionRecord
from ledger.signing import sign_record, verify_signature


def _make_record(**overrides):
    fields = dict(
        id="d1", timestamp="t0", model_version="mv1", prompt_version="pv1",
        data_snapshot="ds1", input="question", output="answer", previous_hash="0" * 64,
    )
    fields.update(overrides)
    return DecisionRecord(**fields)


def test_sign_record_is_deterministic_for_the_same_secret():
    record = _make_record()
    assert sign_record(record, "secret-key") == sign_record(record, "secret-key")


def test_sign_record_differs_for_different_secrets():
    record = _make_record()
    assert sign_record(record, "secret-a") != sign_record(record, "secret-b")


def test_sign_record_accepts_bytes_or_str_secret_identically():
    record = _make_record()
    assert sign_record(record, "secret-key") == sign_record(record, b"secret-key")


def test_verify_signature_accepts_a_valid_signature():
    record = _make_record()
    signature = sign_record(record, "secret-key")
    assert verify_signature(record, signature, "secret-key") is True


def test_verify_signature_rejects_wrong_secret():
    record = _make_record()
    signature = sign_record(record, "secret-key")
    assert verify_signature(record, signature, "wrong-key") is False


def test_verify_signature_rejects_signature_after_tampering():
    record = _make_record()
    signature = sign_record(record, "secret-key")
    tampered = _make_record(output="a different answer")
    assert verify_signature(tampered, signature, "secret-key") is False

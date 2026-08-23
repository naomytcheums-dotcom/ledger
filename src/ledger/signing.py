"""
HMAC-based signing of ledger records -- pure stdlib, no PKI dependency.
Proves a record was written by someone holding a given secret, and
that its content hasn't changed since. This is authenticity, not
identity: a valid signature proves "produced by a holder of this key,"
not which specific person that was -- pair it with one key per
actor/service, not one shared secret for everyone, to get real actor
attribution out of it.
"""

import hashlib
import hmac


def sign_record(record, secret):
    """`secret` is bytes or str. Returns a hex HMAC-SHA256 digest over
    the record's own content hash -- signing the hash, not the raw
    fields, so the signature is short and still covers every field
    (the hash already does)."""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    message = record.record_hash().encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_signature(record, signature, secret):
    """Constant-time comparison -- a naive `==` on the signatures would
    leak timing information about how many leading characters matched,
    a real (if minor) side channel for a function whose whole job is
    verifying authenticity."""
    expected = sign_record(record, secret)
    return hmac.compare_digest(expected, signature)

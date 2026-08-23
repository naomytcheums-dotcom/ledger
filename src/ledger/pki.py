"""
Public-key (Ed25519) record signing -- proves a record was produced by
the holder of a specific PRIVATE key, verifiable by anyone holding only
the matching PUBLIC key. Unlike `signing.py`'s HMAC (a shared secret
both sides must protect equally), this gives real per-actor identity:
one keypair per actor, the private key never leaves that actor, public
keys can be distributed freely for verification.

Needs the optional `cryptography` dependency -- the only module in
this library that does, and the only reason it isn't imported from
`ledger/__init__.py` alongside everything else. Install with
`pip install ledger[pki]` and import directly: `from ledger.pki import ...`.
"""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_keypair():
    """Returns `(private_key, public_key)`. Keep the private key with
    the actor signing records; distribute the public key to anyone who
    needs to verify."""
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def sign_record(record, private_key):
    """Returns a hex-encoded Ed25519 signature over the record's own
    content hash -- signing the hash rather than the raw fields keeps
    the signed message short while still covering every field."""
    message = record.record_hash().encode("utf-8")
    return private_key.sign(message).hex()


def verify_signature(record, signature_hex, public_key):
    """True iff `signature_hex` is a valid signature over `record`'s
    content hash, made by the private key matching `public_key`. Never
    raises -- an invalid signature (forged, wrong key, tampered record)
    is reported as False, not an exception a caller might forget to
    catch, matching `signing.verify_signature`'s contract."""
    message = record.record_hash().encode("utf-8")
    try:
        public_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except InvalidSignature:
        return False


def private_key_to_pem(private_key):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def public_key_to_pem(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def private_key_from_pem(pem_text):
    return serialization.load_pem_private_key(pem_text.encode("utf-8"), password=None)


def public_key_from_pem(pem_text):
    return serialization.load_pem_public_key(pem_text.encode("utf-8"))

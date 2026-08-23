"""
Content-addressed identifiers for the things a decision depends on --
a prompt template, a model, a snapshot of input data -- so "version 3"
never means two different people's different idea of what version 3
actually contained.
"""

from ledger.record import content_hash


def prompt_version(prompt_text):
    return content_hash({"prompt": prompt_text})


def model_version(model_name, model_config=None):
    return content_hash({"model": model_name, "config": model_config or {}})


def data_snapshot(data):
    """`data` is whatever input the decision was actually made from --
    a document, a retrieved context block, a row of structured data.
    Two calls with equal content always produce the same snapshot id,
    regardless of when they're called."""
    return content_hash({"data": data})

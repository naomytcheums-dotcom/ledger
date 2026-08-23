"""
Audit queries over a loaded ledger -- the questions an auditor or
incident responder actually asks: which decisions used this prompt
version, which used this data snapshot, what happened in this time
range. Pure filtering over a list of DecisionRecord; no store or file
access here.
"""


def by_prompt_version(records, prompt_version):
    return [r for r in records if r.prompt_version == prompt_version]


def by_model_version(records, model_version):
    return [r for r in records if r.model_version == model_version]


def by_data_snapshot(records, data_snapshot):
    return [r for r in records if r.data_snapshot == data_snapshot]


def between(records, start_timestamp, end_timestamp):
    """Inclusive range over `timestamp` as plain string comparison --
    correct as long as timestamps are ISO 8601, the same assumption the
    rest of this library makes about that field."""
    return [r for r in records if start_timestamp <= r.timestamp <= end_timestamp]

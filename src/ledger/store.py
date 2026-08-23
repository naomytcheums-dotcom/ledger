"""
An append-only, hash-chained ledger -- each record's `previous_hash`
points at the record before it, so altering or deleting a past record
breaks every hash after it. Backed by a JSONL file: one record per
line, human-readable, diffable, and trivial to append to without
rewriting the whole file.
"""

import json

from ledger.record import DecisionRecord, GENESIS_HASH


class LedgerStore:
    def __init__(self, path):
        self.path = path

    def _last_hash(self):
        records = self.read_all()
        if not records:
            return GENESIS_HASH
        return records[-1].record_hash()

    def append(self, id, timestamp, model_version, prompt_version, data_snapshot, input, output, actor=""):
        record = DecisionRecord(
            id=id,
            timestamp=timestamp,
            model_version=model_version,
            prompt_version=prompt_version,
            data_snapshot=data_snapshot,
            input=input,
            output=output,
            previous_hash=self._last_hash(),
            actor=actor,
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        return record

    def read_all(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = [line for line in f if line.strip()]
        except FileNotFoundError:
            return []
        return [DecisionRecord.from_dict(json.loads(line)) for line in lines]

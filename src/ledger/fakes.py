"""
An in-memory stand-in for LedgerStore, so pipeline code that appends
and queries decisions can be tested without touching disk.
"""

from ledger.record import DecisionRecord, GENESIS_HASH


class InMemoryLedgerStore:
    def __init__(self):
        self._records = []

    def _last_hash(self):
        if not self._records:
            return GENESIS_HASH
        return self._records[-1].record_hash()

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
        self._records.append(record)
        return record

    def read_all(self):
        return list(self._records)

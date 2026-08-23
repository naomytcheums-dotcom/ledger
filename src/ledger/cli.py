"""
Command-line interface for ledger -- verify a chain, take or check a
checkpoint, or run an audit query, without writing any Python. Every
command here is a thin wrapper calling straight into the same library
functions used programmatically elsewhere.
"""

import argparse
import sys

from ledger.checkpoint import CheckpointMismatchError, create_checkpoint, load_checkpoint, save_checkpoint, verify_checkpoint
from ledger.query import between, by_actor, by_data_snapshot, by_model_version, by_prompt_version
from ledger.replay import ChainIntegrityError, verify_chain
from ledger.store import LedgerStore


def _print_record(record):
    print(f"  {record.id}  {record.timestamp}  actor={record.actor or '-'}  input={record.input[:60]!r}")


def cmd_verify(args):
    records = LedgerStore(args.ledger).read_all()
    if not records:
        print(f"{args.ledger}: empty ledger, nothing to verify")
        return 0
    try:
        verify_chain(records)
    except ChainIntegrityError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK: {len(records)} records, chain intact")
    return 0


def cmd_checkpoint_create(args):
    records = LedgerStore(args.ledger).read_all()
    checkpoint = create_checkpoint(records)
    save_checkpoint(args.checkpoint, checkpoint)
    print(f"Checkpoint written to {args.checkpoint}: {checkpoint}")
    return 0


def cmd_checkpoint_verify(args):
    records = LedgerStore(args.ledger).read_all()
    checkpoint = load_checkpoint(args.checkpoint)
    try:
        verify_checkpoint(records, checkpoint)
    except CheckpointMismatchError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK: ledger matches checkpoint ({checkpoint['record_count']} records)")
    return 0


def cmd_query(args):
    records = LedgerStore(args.ledger).read_all()
    if args.prompt_version:
        records = by_prompt_version(records, args.prompt_version)
    if args.model_version:
        records = by_model_version(records, args.model_version)
    if args.data_snapshot:
        records = by_data_snapshot(records, args.data_snapshot)
    if args.actor:
        records = by_actor(records, args.actor)
    if args.since or args.until:
        records = between(records, args.since or "", args.until or "￿")

    print(f"{len(records)} matching record(s):")
    for record in records:
        _print_record(record)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="ledger", description="Inspect and verify a tamper-evident decision ledger.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="verify the hash chain is intact")
    verify_parser.add_argument("ledger", help="path to the ledger .jsonl file")
    verify_parser.set_defaults(func=cmd_verify)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="create or verify an external checkpoint")
    checkpoint_sub = checkpoint_parser.add_subparsers(dest="checkpoint_command", required=True)

    create_parser = checkpoint_sub.add_parser("create")
    create_parser.add_argument("ledger")
    create_parser.add_argument("checkpoint")
    create_parser.set_defaults(func=cmd_checkpoint_create)

    verify_cp_parser = checkpoint_sub.add_parser("verify")
    verify_cp_parser.add_argument("ledger")
    verify_cp_parser.add_argument("checkpoint")
    verify_cp_parser.set_defaults(func=cmd_checkpoint_verify)

    query_parser = subparsers.add_parser("query", help="filter records in a ledger")
    query_parser.add_argument("ledger")
    query_parser.add_argument("--prompt-version")
    query_parser.add_argument("--model-version")
    query_parser.add_argument("--data-snapshot")
    query_parser.add_argument("--actor")
    query_parser.add_argument("--since", help="ISO 8601 timestamp, inclusive lower bound")
    query_parser.add_argument("--until", help="ISO 8601 timestamp, inclusive upper bound")
    query_parser.set_defaults(func=cmd_query)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

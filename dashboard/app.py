"""
Browse and verify a ledger visually instead of via the CLI. Deliberately
uncached: for a tamper-evidence viewer, showing a stale cached "verified"
status while the underlying file changed would be actively misleading,
so every rerun re-reads the file from disk.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from ledger.checkpoint import CheckpointMismatchError, load_checkpoint, verify_checkpoint
from ledger.query import between, by_actor, by_data_snapshot, by_model_version, by_prompt_version
from ledger.replay import ChainIntegrityError, verify_chain
from ledger.store import LedgerStore

st.set_page_config(page_title="ledger", page_icon=":material/verified:", layout="wide")

DEFAULT_LEDGER_PATH = str(Path(__file__).parent.parent / "demo_ledger.jsonl")

st.title("ledger — audit trail viewer")

with st.sidebar:
    st.subheader("Ledger")
    ledger_path = st.text_input("Path to .jsonl ledger file", value=DEFAULT_LEDGER_PATH)
    checkpoint_path = st.text_input("Path to a checkpoint .json file (optional)", value="")

    st.subheader("Filters")
    actor_filter = st.text_input("Actor")
    prompt_version_filter = st.text_input("Prompt version")
    model_version_filter = st.text_input("Model version")
    data_snapshot_filter = st.text_input("Data snapshot")
    since = st.text_input("Since (ISO 8601)", value="")
    until = st.text_input("Until (ISO 8601)", value="")

if not Path(ledger_path).exists():
    st.info("Enter the path to a ledger .jsonl file in the sidebar to get started.")
    st.stop()

records = LedgerStore(ledger_path).read_all()

if not records:
    st.info(f"{ledger_path} exists but has no records yet.")
    st.stop()

try:
    verify_chain(records)
    chain_status = "Intact"
except ChainIntegrityError as exc:
    chain_status = f"Broken: {exc}"

with st.container(horizontal=True):
    st.metric("Records", len(records), border=True)
    st.metric("Chain status", "Intact" if chain_status == "Intact" else "Broken", border=True)
    st.metric("Distinct actors", len({r.actor for r in records if r.actor}), border=True)
    st.metric("Distinct prompt versions", len({r.prompt_version for r in records}), border=True)

if chain_status != "Intact":
    st.error(chain_status, icon=":material/error:")
else:
    st.success("Every record's hash links correctly to the one before it.", icon=":material/verified:")

if checkpoint_path:
    if not Path(checkpoint_path).exists():
        st.warning(f"Checkpoint file not found: {checkpoint_path}")
    else:
        checkpoint = load_checkpoint(checkpoint_path)
        try:
            verify_checkpoint(records, checkpoint)
            st.success(
                f"Checkpoint verified: matches the ledger at {checkpoint['record_count']} records.",
                icon=":material/verified_user:",
            )
        except CheckpointMismatchError as exc:
            st.error(f"Checkpoint mismatch: {exc}", icon=":material/gpp_maybe:")

filtered = records
if actor_filter:
    filtered = by_actor(filtered, actor_filter)
if prompt_version_filter:
    filtered = by_prompt_version(filtered, prompt_version_filter)
if model_version_filter:
    filtered = by_model_version(filtered, model_version_filter)
if data_snapshot_filter:
    filtered = by_data_snapshot(filtered, data_snapshot_filter)
if since or until:
    filtered = between(filtered, since or "", until or "￿")

with st.container(border=True):
    st.subheader(f"Decisions ({len(filtered)} of {len(records)})")
    table = pd.DataFrame(
        [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "actor": r.actor or "-",
                "model_version": r.model_version[:12] + "...",
                "prompt_version": r.prompt_version[:12] + "...",
                "input": r.input,
                "output": r.output,
            }
            for r in filtered
        ]
    )
    st.dataframe(table, hide_index=True)

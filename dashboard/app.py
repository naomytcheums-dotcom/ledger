"""
Browse and verify a ledger visually instead of via the CLI. Deliberately
uncached: for a tamper-evidence viewer, showing a stale cached "verified"
status while the underlying file changed would be actively misleading,
so every rerun re-reads the file from disk.

Demo data is seeded into a per-session temp directory on click, not a
fixed path -- the same class of bug already caught and fixed in this
portfolio's llm-observatory dashboard: a shared fixed path means every
visitor on a multi-user deployment reads and writes the same file.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from ledger import LedgerStore, data_snapshot, model_version, prompt_version
from ledger.checkpoint import CheckpointMismatchError, create_checkpoint, load_checkpoint, save_checkpoint, verify_checkpoint
from ledger.query import between, by_actor, by_data_snapshot, by_model_version, by_prompt_version
from ledger.replay import ChainIntegrityError, verify_chain

st.set_page_config(page_title="ledger", page_icon=":material/verified:", layout="wide")

st.title("ledger — audit trail viewer")


def _seed_demo_ledger(path):
    store = LedgerStore(path)
    mv = model_version("claude-sonnet-5")
    pv = prompt_version("Answer the user question, citing sources.")
    snapshot = data_snapshot({"docs_version": "v1.2"})
    questions = [
        ("How do I add a path parameter?", "service:rag-fastapi-assistant"),
        ("Does the framework support server-sent events?", "service:rag-fastapi-assistant"),
        ("What is the difference between Depends and Security?", "service:rag-fastapi-assistant"),
        ("Summarize the incident from last night.", "service:llm-observatory"),
    ]
    for i, (question, actor) in enumerate(questions):
        store.append(
            id=f"decision-{i}",
            timestamp=f"2026-08-23T10:0{i}:00Z",
            model_version=mv,
            prompt_version=pv,
            data_snapshot=snapshot,
            input=question,
            output=f"[answer to: {question}]",
            actor=actor,
        )
    return store


if "ledger_session_dir" not in st.session_state:
    st.session_state.ledger_session_dir = tempfile.mkdtemp()

with st.sidebar:
    st.subheader("Ledger")
    if st.button("Load demo data", icon=":material/dataset:"):
        session_dir = Path(st.session_state.ledger_session_dir)
        demo_ledger_path = session_dir / "demo_ledger.jsonl"
        demo_checkpoint_path = session_dir / "demo_checkpoint.json"

        if demo_ledger_path.exists():
            demo_ledger_path.unlink()  # reset to a clean 4-record demo, not append onto a previous click

        store = _seed_demo_ledger(demo_ledger_path)
        save_checkpoint(demo_checkpoint_path, create_checkpoint(store.read_all()))

        st.session_state.ledger_path_value = str(demo_ledger_path)
        st.session_state.checkpoint_path_value = str(demo_checkpoint_path)

    ledger_path = st.text_input("Path to .jsonl ledger file", value=st.session_state.get("ledger_path_value", ""))
    checkpoint_path = st.text_input(
        "Path to a checkpoint .json file (optional)", value=st.session_state.get("checkpoint_path_value", "")
    )

    st.subheader("Filters")
    actor_filter = st.text_input("Actor")
    prompt_version_filter = st.text_input("Prompt version")
    model_version_filter = st.text_input("Model version")
    data_snapshot_filter = st.text_input("Data snapshot")
    since = st.text_input("Since (ISO 8601)", value="")
    until = st.text_input("Until (ISO 8601)", value="")

if not ledger_path:
    st.info("Click **Load demo data** in the sidebar, or enter the path to your own .jsonl ledger file.")
    st.stop()

if not Path(ledger_path).exists():
    st.warning(f"No file found at {ledger_path}.")
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
    st.caption("Full model/prompt version hashes shown below -- copy one straight into a filter above to test it.")
    table = pd.DataFrame(
        [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "actor": r.actor or "-",
                "model_version": r.model_version,
                "prompt_version": r.prompt_version,
                "input": r.input,
                "output": r.output,
            }
            for r in filtered
        ]
    )
    st.dataframe(
        table,
        hide_index=True,
        column_config={
            "model_version": st.column_config.TextColumn(width="medium"),
            "prompt_version": st.column_config.TextColumn(width="medium"),
        },
    )

import json
import os
import pathlib
import queue
import sys
import threading
import time

import streamlit as st
from loguru import logger

# ── path setup ────────────────────────────────────────────────────────────────
_ROOT = pathlib.Path(__file__).parent.parent
_BACKEND = _ROOT / "backend"
_SETTINGS_FILE = pathlib.Path(__file__).parent / "settings.json"
sys.path.insert(0, str(_BACKEND))

from agents.curator import list_digests  # noqa: E402
from crew import run  # noqa: E402

# ── settings helpers ───────────────────────────────────────────────────────────

def _load_settings() -> dict:
    try:
        return json.loads(_SETTINGS_FILE.read_text())
    except Exception:
        return {"topics": ["AI agent frameworks 2025", "large language model research"], "to_email": ""}


def _save_settings(topics: list[str], to_email: str) -> None:
    _SETTINGS_FILE.write_text(json.dumps({"topics": topics, "to_email": to_email}, indent=2))


# ── session state init ─────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "running": False,
        "logs": [],
        "digests": None,
        "log_queue": queue.Queue(),
        "sink_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── log drain ─────────────────────────────────────────────────────────────────

def _drain_logs() -> None:
    q: queue.Queue = st.session_state.log_queue
    while not q.empty():
        try:
            st.session_state.logs.append(q.get_nowait())
        except queue.Empty:
            break


# ── pipeline thread ───────────────────────────────────────────────────────────

def _run_pipeline(topics: list[str], to_email: str) -> None:
    if to_email:
        os.environ["TO_EMAIL"] = to_email

    sink_id = logger.add(
        lambda msg: st.session_state.log_queue.put(msg.strip()),
        format="{time:HH:mm:ss} {level:<7} {message}",
        level="INFO",
        colorize=False,
    )
    st.session_state.sink_id = sink_id

    try:
        digests = run(topics=topics)
        st.session_state.digests = digests
    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}")
        st.session_state.digests = []
    finally:
        logger.remove(sink_id)
        st.session_state.sink_id = None
        st.session_state.running = False


# ── digest renderer ────────────────────────────────────────────────────────────

def _render_digest(digest) -> None:
    st.markdown(f"### {digest.topic}")
    st.caption(f"{digest.included_articles} of {digest.total_articles} articles kept")

    st.markdown("**Overview**")
    st.markdown(digest.overview)

    st.markdown("**Key Insights**")
    for insight in digest.key_insights:
        st.markdown(f"- {insight}")

    for section in digest.sections:
        st.markdown(f"**{section.heading}**")
        st.markdown(section.body)

    with st.expander("Sources"):
        for url in digest.sources:
            st.markdown(f"- [{url}]({url})")


# ── main ───────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Research Digest", layout="wide")
_init_state()
settings = _load_settings()

# ── sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")

    topics_text = st.text_area(
        "Topics (one per line)",
        value="\n".join(settings["topics"]),
        height=120,
        help="Each line becomes a separate search topic.",
    )

    to_email = st.text_input(
        "Email recipient",
        value=settings["to_email"],
        placeholder="you@example.com",
    )

    if st.button("Save settings"):
        new_topics = [t.strip() for t in topics_text.splitlines() if t.strip()]
        _save_settings(new_topics, to_email)
        st.success("Saved.")

    st.divider()
    st.caption("Schedule: on-demand only — click Run Now to trigger a digest.")

# ── main panel ─────────────────────────────────────────────────────────────────

st.title("Research Digest")

active_topics = [t.strip() for t in topics_text.splitlines() if t.strip()]
st.caption("Tracking: " + " · ".join(f"`{t}`" for t in active_topics))

run_clicked = st.button(
    "Run Now",
    disabled=st.session_state.running,
    type="primary",
)

if run_clicked and not st.session_state.running:
    st.session_state.running = True
    st.session_state.logs = []
    st.session_state.digests = None
    t = threading.Thread(
        target=_run_pipeline,
        args=(active_topics, to_email),
        daemon=True,
    )
    t.start()

# ── live log ──────────────────────────────────────────────────────────────────

_drain_logs()

if st.session_state.running or st.session_state.logs:
    with st.expander("Live log", expanded=st.session_state.running):
        if st.session_state.running:
            st.spinner("Running pipeline...")
        log_text = "\n".join(st.session_state.logs) if st.session_state.logs else "Starting…"
        st.code(log_text, language=None)

if st.session_state.running:
    time.sleep(2)
    st.rerun()

# ── digest preview ────────────────────────────────────────────────────────────

if st.session_state.digests:
    st.divider()
    st.subheader("Latest Run")
    for digest in st.session_state.digests:
        _render_digest(digest)
        st.divider()
elif st.session_state.digests is not None and not st.session_state.running:
    st.info("Run complete — no new articles found (all already seen).")

# ── history ───────────────────────────────────────────────────────────────────

st.subheader("History")
rows = list_digests(limit=20)

if not rows:
    st.caption("No digests yet — run the pipeline to create one.")
else:
    import pandas as pd

    summary_df = pd.DataFrame([
        {"#": r["id"], "Topic": r["topic"], "Run at (UTC)": r["run_at"]}
        for r in rows
    ])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.markdown("#### Details")
    for row in rows:
        label = f"#{row['id']} — {row['topic']} ({row['run_at'][:16]})"
        with st.expander(label):
            try:
                import json as _json
                from agents.writer import Digest
                digest = Digest.model_validate(_json.loads(row["digest_json"]))
                _render_digest(digest)
            except Exception as exc:
                st.error(f"Could not parse digest: {exc}")
                st.code(row["digest_json"])

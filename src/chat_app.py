from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

from pro_agent import (
    add_approval,
    add_tracker_row,
    get_approvals,
    get_memory,
    get_tracker,
    pro_chat,
    run_pro_task,
    update_approval,
)


load_dotenv()


ROOT = Path(__file__).resolve().parents[1]


st.set_page_config(page_title="Franzik", page_icon="AI", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #0d1117; color: #f0f4fb; }
    [data-testid="stSidebar"] { background: #111827; border-right: 1px solid #283244; }
    .hero {
        padding: 1rem 0 0.8rem 0;
        border-bottom: 1px solid #283244;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 1.9rem;
        font-weight: 750;
        letter-spacing: 0;
        margin: 0;
    }
    .hero-sub {
        color: #a9b4c7;
        font-size: 0.95rem;
        margin-top: 0.25rem;
    }
    .agent-card {
        border: 1px solid #283244;
        background: #121a27;
        border-radius: 8px;
        padding: 0.9rem;
    }
    .small-muted { color: #a9b4c7; font-size: 0.88rem; }
    .stButton button, .stDownloadButton button { border-radius: 8px; }
    textarea { min-height: 160px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("document_context", "")
    st.session_state.setdefault("last_report", "")
    st.session_state.setdefault("last_sources", [])
    st.session_state.setdefault("use_profile", True)
    st.session_state.setdefault("live_research", True)


def extract_uploaded_file(uploaded_file) -> str:
    name = uploaded_file.name
    suffix = Path(name).suffix.lower()
    data = uploaded_file.getvalue()

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages[:30]]
        return f"# Uploaded PDF: {name}\n\n" + "\n".join(pages).strip()
    if suffix in {".txt", ".md"}:
        return f"# Uploaded Text: {name}\n\n" + data.decode("utf-8", errors="ignore")
    if suffix == ".csv":
        df = pd.read_csv(BytesIO(data))
        return f"# Uploaded CSV: {name}\n\n{df.head(50).to_markdown(index=False)}"
    if suffix in {".xlsx", ".xls"}:
        excel = pd.ExcelFile(BytesIO(data))
        parts = [f"# Uploaded Spreadsheet: {name}"]
        for sheet in excel.sheet_names[:5]:
            parts.append(f"## {sheet}\n\n{excel.parse(sheet).head(50).to_markdown(index=False)}")
        return "\n\n".join(parts)
    return f"# Uploaded File: {name}\n\nNo text extractor exists for this file type yet."


def chat_export_text() -> str:
    lines = ["# Franzik Chat Export", ""]
    for message in st.session_state.messages:
        lines.append(f"## {message['role'].title()}")
        lines.append(message["content"])
        lines.append("")
    return "\n".join(lines)


init_state()

for secret_name in ["GROQ_API_KEY", "GROQ_BASE_URL", "GROQ_MODEL", "TAVILY_API_KEY", "SERPAPI_API_KEY"]:
    try:
        if not os.environ.get(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except Exception:
        pass

with st.sidebar:
    st.markdown("## Franzik")
    st.caption("Research. Plan. Execute.")

    groq_key = st.text_input(
        "Groq API key",
        value="",
        type="password",
        help="Optional. Public users can bring their own key. It is kept only in this app session.",
    )
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    mode = st.selectbox(
        "Agent mode",
        ["Auto", "Europe University", "Europe Jobs", "Document Writer", "Code Builder", "Research", "Verifier"],
    )
    st.session_state.use_profile = st.toggle("Use redacted profile", value=st.session_state.use_profile)
    st.session_state.live_research = st.toggle("Live web research", value=st.session_state.live_research)
    max_results = st.slider("Results per query", 2, 8, 4)

    st.divider()
    files = st.file_uploader(
        "Attach context",
        type=["pdf", "txt", "md", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )
    if files and st.button("Read attachments"):
        st.session_state.document_context = "\n\n---\n\n".join(extract_uploaded_file(file) for file in files)
        st.success(f"Loaded {len(files)} file(s)")

    if st.session_state.document_context:
        with st.expander("Loaded context"):
            st.text(st.session_state.document_context[:3000])

    st.divider()
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.session_state.last_report = ""
        st.session_state.last_sources = []
        st.rerun()

    st.download_button("Download chat", chat_export_text(), file_name="franzik_chat.md")

st.markdown(
    """
    <div class="hero">
      <div class="hero-title">Franzik</div>
      <div class="hero-sub">Research, plan, analyze, and execute tasks with AI-powered workflows.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not os.environ.get("GROQ_API_KEY"):
    st.warning("Add a Groq API key in the sidebar or set `GROQ_API_KEY` in deployment secrets before running model tasks.")

metric_cols = st.columns(5)
metric_cols[0].metric("Mode", mode)
metric_cols[1].metric("Memory", len(get_memory()))
metric_cols[2].metric("Approvals", len([item for item in get_approvals() if item["status"] == "PENDING"]))
metric_cols[3].metric("Tracker", len(get_tracker()))
metric_cols[4].metric("Research", "On" if st.session_state.live_research else "Off")

tab_chat, tab_pro, tab_approvals, tab_tracker, tab_memory = st.tabs(
    ["Chat", "Pro Task", "Approvals", "Tracker", "Memory"]
)

with tab_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask the agent anything, or tell it to prepare work.")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = pro_chat(
                    prompt,
                    mode=mode,
                    document_context=st.session_state.document_context,
                    use_profile=st.session_state.use_profile,
                )
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

with tab_pro:
    st.markdown("### Run A Pro Task")
    task_type = st.selectbox(
        "Task type",
        ["Auto", "University", "Jobs", "Documents", "Research", "Coding", "Verification"],
        index=0,
    )
    instruction = st.text_area(
        "Instruction",
        value="Find free or low-tuition public universities in Europe for AI/Data Science master's where I am eligible, rank them, and prepare my next actions.",
    )
    run_col, approve_col = st.columns([1, 1])
    if run_col.button("Run pro agent", type="primary"):
        with st.spinner("Researching, planning, verifying, and creating approval items..."):
            result = run_pro_task(
                instruction=instruction,
                task_type=task_type,
                live_research=st.session_state.live_research,
                max_results=max_results,
            )
        st.session_state.last_report = result["report"]
        st.session_state.last_sources = result["sources"]
        st.success(f"Run saved: {result['run_id']}")
        st.rerun()

    if approve_col.button("Add manual approval item"):
        add_approval(
            title="Manual approval request",
            action=instruction,
            risk="User must review before external action.",
            payload=instruction,
        )
        st.success("Added to approval queue")

    if st.session_state.last_report:
        st.markdown("### Latest Run Report")
        st.markdown(st.session_state.last_report)
        st.download_button(
            "Download report",
            st.session_state.last_report,
            file_name="pro_agent_run.md",
        )
        if st.session_state.last_sources:
            st.markdown("### Sources")
            for source in st.session_state.last_sources:
                st.markdown(f"- [{source.get('title')}]({source.get('url')})  \n  {source.get('snippet', '')}")

with tab_approvals:
    st.markdown("### Approval Queue")
    approvals = get_approvals()
    if not approvals:
        st.info("No approval items yet.")
    for item in approvals:
        with st.expander(f"{item['status']} · {item['title']} · {item['id']}"):
            st.markdown(f"**Action:** {item['action']}")
            st.markdown(f"**Risk:** {item['risk']}")
            st.text_area("Payload", item["payload"], height=220, key=f"payload_{item['id']}")
            col_a, col_b, col_c = st.columns(3)
            if col_a.button("Approve", key=f"approve_{item['id']}"):
                update_approval(item["id"], "APPROVED")
                st.rerun()
            if col_b.button("Reject", key=f"reject_{item['id']}"):
                update_approval(item["id"], "REJECTED")
                st.rerun()
            if col_c.button("Mark done", key=f"done_{item['id']}"):
                update_approval(item["id"], "DONE")
                st.rerun()

with tab_tracker:
    st.markdown("### Opportunity Tracker")
    rows = get_tracker()
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.download_button(
            "Download tracker JSON",
            pd.DataFrame(rows).to_json(orient="records", indent=2),
            file_name="opportunity_tracker.json",
        )
    else:
        st.info("Run a pro task to create tracker entries.")

    with st.expander("Add tracker row"):
        title = st.text_input("Title")
        kind = st.selectbox("Kind", ["University", "Job", "Scholarship", "Document", "Other"])
        status = st.selectbox("Status", ["DISCOVERED", "RESEARCHED", "DRAFTING", "READY_FOR_APPROVAL", "APPLIED", "REJECTED", "ACCEPTED"])
        link = st.text_input("Link")
        notes = st.text_area("Notes")
        if st.button("Save tracker row"):
            add_tracker_row({"kind": kind, "title": title, "status": status, "link": link, "notes": notes})
            st.rerun()

with tab_memory:
    st.markdown("### Durable Memory")
    memory = get_memory()
    if memory:
        for item in memory[:50]:
            with st.expander(f"{item.get('created_at')} · {item.get('type')} · {item.get('task_type', '')}"):
                st.json(item)
    else:
        st.info("No memory yet.")

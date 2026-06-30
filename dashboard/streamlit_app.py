"""
InsightForge dashboard — a Streamlit frontend that talks to the FastAPI backend.

This is the whole platform in one screen: upload a file (or scrape a URL), see the
data profiled with charts, then generate an AI analysis — all by calling the API
endpoints we built in Phases 1-4. Pure Python, front to back.

Run the API first (uvicorn app.main:app), then:  streamlit run dashboard.py
"""

import io
import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="InsightForge", page_icon="✶", layout="wide")

# ── Brand touch (colors come from the dark theme in .streamlit/config.toml) ──────
st.markdown(
    """
    <style>
      /* square, uppercase buttons — the monochrome look, without fighting the theme */
      .stButton button, .stDownloadButton button {
        border-radius: 0 !important;
        text-transform: uppercase;
        letter-spacing: .08em;
        font-weight: 600;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar: backend connection ────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Backend")
    # API URL: env var (Streamlit Cloud also exposes secrets as env vars) → deployed default.
    # Override anytime in the field (e.g. http://127.0.0.1:8000 for local dev).
    default_api = os.environ.get("INSIGHTFORGE_API", "https://insightforge-api-na2a.onrender.com")
    api = st.text_input("API base URL", value=default_api).rstrip("/")
    try:
        h = requests.get(f"{api}/health", timeout=4).json()
        ai_on = h.get("ai_configured")
        st.success(f"Connected · {h.get('app')}")
        st.caption(f"AI key: {'✓ configured' if ai_on else '✗ not set'}")
    except Exception:
        st.error("Can't reach the API. Start it with `uvicorn app.main:app`.")

st.title("✶ InsightForge")
st.caption("Upload data or scrape a URL → profile it → get an AI analysis. One platform, all Python.")


def show_profile(profile: dict):
    """Render a DataProfile (from /data/analyze or /scrape/table) with metrics + charts."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{profile['rows']:,}")
    c2.metric("Columns", profile["columns"])
    c3.metric("Duplicate rows", profile["duplicate_rows"])

    cols = profile["column_profiles"]
    table = pd.DataFrame(
        [
            {
                "column": c["name"],
                "type": c["dtype"],
                "nulls": c["nulls"],
                "null %": c["null_pct"],
                "unique": c["unique"],
                "mean": (c["numeric"] or {}).get("mean"),
            }
            for c in cols
        ]
    )
    st.subheader("Column profile")
    st.dataframe(table, use_container_width=True, hide_index=True)

    left, right = st.columns(2)
    with left:
        st.caption("Missing values (%) by column")
        st.bar_chart(table.set_index("column")["null %"])
    with right:
        st.caption("Unique values by column")
        st.bar_chart(table.set_index("column")["unique"])

    numeric = table.dropna(subset=["mean"]).copy()
    rows_total = profile["rows"]

    def _is_id(name, uniq) -> bool:
        # Averaging an identifier column is meaningless — skip those.
        n = str(name).lower()
        return n == "id" or n.endswith("_id") or n.startswith("id_") or uniq == rows_total

    numeric = numeric[~numeric.apply(lambda r: _is_id(r["column"], r["unique"]), axis=1)]
    if not numeric.empty:
        st.caption("Mean of numeric columns (identifiers excluded)")
        st.bar_chart(numeric.set_index("column")["mean"])


# ── Inputs ─────────────────────────────────────────────────────────────────────
tab_file, tab_url, tab_agent = st.tabs(["📁 Upload file", "🌐 From URL", "🤖 Research agent"])

with tab_file:
    up = st.file_uploader("CSV or Excel", type=["csv", "xlsx", "xls"])
    q_file = st.text_input("Optional question for the AI", key="qf")
    if st.button("Analyze file", key="bf") and up is not None:
        raw = up.getvalue()
        st.session_state["mode"] = "file"
        st.session_state["payload"] = {"name": up.name, "bytes": raw, "question": q_file}
        with st.spinner("Profiling…"):
            r = requests.post(f"{api}/data/analyze",
                              files={"file": (up.name, io.BytesIO(raw), "application/octet-stream")},
                              timeout=60)
        st.session_state["profile"] = r.json() if r.ok else None
        st.session_state["error"] = None if r.ok else r.text
        st.session_state.pop("insights", None)

with tab_url:
    url = st.text_input("Page URL with a table", placeholder="https://…")
    q_url = st.text_input("Optional question for the AI", key="qu")
    if st.button("Scrape & analyze", key="bu") and url:
        st.session_state["mode"] = "url"
        st.session_state["payload"] = {"url": url, "question": q_url}
        with st.spinner("Scraping & profiling…"):
            r = requests.post(f"{api}/scrape/table", json={"url": url}, timeout=60)
        st.session_state["profile"] = r.json() if r.ok else None
        st.session_state["error"] = None if r.ok else r.text
        st.session_state.pop("insights", None)

with tab_agent:
    st.caption("Give it a goal and a few URLs — it plans what to compare, scrapes each page, "
               "then writes one grounded report. The whole loop runs itself.")
    ag_goal = st.text_area(
        "Goal",
        placeholder="Compare these competitors and summarize each one's strengths and weaknesses.",
        key="ag_goal",
    )
    ag_urls = st.text_area("URLs (one per line, up to 5)", placeholder="https://…\nhttps://…", key="ag_urls")
    if st.button("Run agent", key="ba"):
        urls = [u.strip() for u in ag_urls.splitlines() if u.strip()]
        if not ag_goal.strip() or not urls:
            st.warning("Enter a goal and at least one URL.")
        else:
            with st.spinner("Planning → gathering → synthesizing…"):
                r = requests.post(f"{api}/agent/research",
                                  json={"goal": ag_goal, "urls": urls}, timeout=120)
            st.session_state["agent_result"] = r.json() if r.ok else None
            st.session_state["agent_error"] = None if r.ok else r.text

    if st.session_state.get("agent_error"):
        st.error(st.session_state["agent_error"])

    res = st.session_state.get("agent_result")
    if res:
        st.divider()
        st.caption("Focus dimensions the agent chose")
        st.write(" · ".join(res["focus"]))

        with st.expander("Agent steps", expanded=True):
            for s in res["steps"]:
                st.markdown(
                    f"**{s['phase']}** — {s['summary']}  \n"
                    f"<span style='color:#888;font-size:0.85em'>{s['detail']}</span>",
                    unsafe_allow_html=True,
                )

        st.caption("Sources gathered")
        for s in res["sources"]:
            if s.get("error"):
                st.markdown(f"- ⚠ {s['url']} — {s['error']}")
            else:
                st.markdown(f"- **{s.get('title') or s['url']}** — {s.get('text_chars', 0):,} chars read")

        st.subheader("Report")
        st.markdown(res["report"])

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.get("error"):
    st.error(st.session_state["error"])

if st.session_state.get("profile"):
    st.divider()
    show_profile(st.session_state["profile"])

    # ── Downloadable reports (file mode) ──
    if st.session_state.get("mode") == "file":
        st.divider()
        if st.button("📥 Prepare downloadable reports"):
            pl = st.session_state["payload"]
            with st.spinner("Building Excel + PDF…"):
                xl = requests.post(f"{api}/report/excel",
                                  files={"file": (pl["name"], io.BytesIO(pl["bytes"]), "application/octet-stream")},
                                  timeout=60)
                pdf = requests.post(f"{api}/report/pdf",
                                   files={"file": (pl["name"], io.BytesIO(pl["bytes"]), "application/octet-stream")},
                                   data={"include_ai": "true"}, timeout=90)
            st.session_state["xlsx"] = xl.content if xl.ok else None
            st.session_state["pdf"] = pdf.content if pdf.ok else None
        c1, c2 = st.columns(2)
        if st.session_state.get("xlsx"):
            c1.download_button("⬇ Excel report", st.session_state["xlsx"],
                               file_name="insightforge-report.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if st.session_state.get("pdf"):
            c2.download_button("⬇ PDF report (with AI)", st.session_state["pdf"],
                               file_name="insightforge-report.pdf", mime="application/pdf")

    st.divider()
    if st.button("🧠 Generate AI insights"):
        mode = st.session_state["mode"]
        pl = st.session_state["payload"]
        with st.spinner("Asking the AI…"):
            if mode == "file":
                r = requests.post(f"{api}/insights/file",
                                  files={"file": (pl["name"], io.BytesIO(pl["bytes"]), "application/octet-stream")},
                                  data={"question": pl["question"]}, timeout=90)
            else:
                r = requests.post(f"{api}/insights/url",
                                  json={"url": pl["url"], "question": pl["question"]}, timeout=90)
        st.session_state["insights"] = r.json().get("insights") if r.ok else None
        if not r.ok:
            st.error(r.text)

    if st.session_state.get("insights"):
        st.subheader("AI analysis")
        st.markdown(st.session_state["insights"])

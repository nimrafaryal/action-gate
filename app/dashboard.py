"""
ACTION GATE — Streamlit security console.

Every list, number, example and rule shown here is fetched from the
FastAPI backend at runtime. Nothing in this file is demo data.
"""

import html
import json
import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("ACTION_GATE_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="ACTION GATE · AI Agent Security Layer",
                   page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------- #
# Design system
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
:root{
  --bg:#06080f; --panel:rgba(14,21,36,.78); --panel-solid:#0e1524;
  --border:rgba(94,234,212,.12); --text:#e8eef8; --muted:#8b97b0;
  --accent:#22d3ee; --accent2:#6366f1; --glow:rgba(34,211,238,.28);
  --allow:#34d399; --approve:#fbbf24; --block:#fb7185; --info:#7dd3fc;
}
html, body, [class*="css"], .stApp { font-family:'IBM Plex Sans',sans-serif; }
.stApp{
  background:
    radial-gradient(1100px 520px at -8% -12%, rgba(99,102,241,.22), transparent 55%),
    radial-gradient(900px 480px at 108% 0%, rgba(34,211,238,.16), transparent 58%),
    radial-gradient(700px 400px at 50% 120%, rgba(52,211,153,.06), transparent 50%),
    linear-gradient(180deg, #070b16 0%, var(--bg) 40%, #05070c 100%);
  color:var(--text);
}
[data-testid="stSidebar"]{
  background:linear-gradient(180deg, #0a101c 0%, #070b14 100%);
  border-right:1px solid var(--border);
}
[data-testid="stSidebar"] *{ color:var(--text) !important; }
[data-testid="stHeader"]{ background:transparent; }
.block-container{ padding-top:1.6rem; max-width:1400px; }
h1,h2,h3{ letter-spacing:-.03em; color:var(--text); }
code, pre, .mono{ font-family:'IBM Plex Mono',monospace !important; }

.hero{ padding:28px 32px; border-radius:22px; border:1px solid var(--border);
  background:linear-gradient(135deg, rgba(34,211,238,.14), rgba(99,102,241,.10) 46%, rgba(14,21,36,.7));
  margin-bottom:22px; position:relative; overflow:hidden; animation:fadeUp .5s ease both;
  box-shadow:0 18px 50px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06); }
.hero:after{ content:""; position:absolute; inset:-50% -8% auto auto; width:420px; height:420px;
  background:radial-gradient(circle, rgba(34,211,238,.32), transparent 64%); filter:blur(18px);
  animation:pulse 7s ease-in-out infinite; }
.hero h1{ margin:0; font-size:2.35rem; font-weight:700;
  background:linear-gradient(90deg,#f8fbff 10%, #67e8f9 55%, #a5b4fc 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hero p{ color:var(--muted); margin:.4rem 0 0; font-size:1.02rem; }
.pill{ display:inline-flex; align-items:center; gap:6px; padding:4px 11px; border-radius:999px;
  font-size:.74rem; font-weight:600; border:1px solid var(--border);
  background:rgba(8,14,26,.55); color:var(--text); margin-right:6px; }
.dot{ width:7px; height:7px; border-radius:50%; display:inline-block; }
.dot.live{ background:var(--allow); box-shadow:0 0 10px var(--allow); animation:blink 1.6s infinite; }

.card{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:18px 20px;
  backdrop-filter:blur(14px); transition:transform .2s ease, border-color .2s ease, box-shadow .2s ease;
  animation:fadeUp .45s ease both; box-shadow:0 10px 28px rgba(0,0,0,.22); }
.card:hover{ transform:translateY(-2px); border-color:rgba(34,211,238,.38);
  box-shadow:0 14px 36px rgba(34,211,238,.08); }
.kpi-label{ color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; font-weight:600; }
.kpi-value{ font-size:2rem; font-weight:700; margin-top:4px; font-variant-numeric:tabular-nums; }
.kpi-sub{ color:var(--muted); font-size:.8rem; }

.verdict{ border-radius:18px; padding:20px 24px; border:1px solid; margin:6px 0 16px; animation:fadeUp .4s ease both; }
.verdict h2{ margin:0; font-size:1.6rem; font-weight:700; }
.verdict p{ margin:.4rem 0 0; color:var(--text); opacity:.85; }
.v-ALLOW{ background:rgba(52,211,153,.10); border-color:rgba(52,211,153,.42); }
.v-ALLOW h2{ color:var(--allow); }
.v-REQUIRE_APPROVAL{ background:rgba(251,191,36,.10); border-color:rgba(251,191,36,.42); }
.v-REQUIRE_APPROVAL h2{ color:var(--approve); }
.v-BLOCK{ background:rgba(251,113,133,.10); border-color:rgba(251,113,133,.48); }
.v-BLOCK h2{ color:var(--block); }

.badge{ padding:3px 10px; border-radius:999px; font-size:.72rem; font-weight:700; letter-spacing:.03em; }
.b-ALLOW{ background:rgba(52,211,153,.16); color:var(--allow); }
.b-REQUIRE_APPROVAL{ background:rgba(251,191,36,.16); color:var(--approve); }
.b-BLOCK, .b-ERROR{ background:rgba(251,113,133,.16); color:var(--block); }
.b-CRITICAL{ background:rgba(251,113,133,.22); color:#fda4af; }
.b-HIGH{ background:rgba(251,191,36,.18); color:var(--approve); }
.b-tool{ background:rgba(125,211,252,.13); color:var(--info); font-family:'IBM Plex Mono',monospace; }

.timeline{ position:relative; padding-left:28px; }
.timeline:before{ content:""; position:absolute; left:10px; top:6px; bottom:6px; width:2px;
  background:linear-gradient(var(--accent), rgba(99,102,241,.35), rgba(255,255,255,.05)); }
.step{ position:relative; margin-bottom:12px; animation:fadeUp .4s ease both; }
.step:before{ content:""; position:absolute; left:-24px; top:20px; width:12px; height:12px; border-radius:50%;
  border:2px solid var(--bg); }
.step.s-ALLOW:before{ background:var(--allow); } .step.s-REQUIRE_APPROVAL:before{ background:var(--approve); }
.step.s-BLOCK:before{ background:var(--block); box-shadow:0 0 12px var(--block); }
.step .head{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.step .summary{ margin:.45rem 0 .2rem; }
.step .args{ color:var(--muted); font-size:.78rem; font-family:'IBM Plex Mono',monospace; word-break:break-all; }
.fx{ color:#67e8f9; font-size:.86rem; margin-top:4px; }
.finding{ color:var(--approve); font-size:.84rem; margin-top:3px; }

.stButton>button{ border-radius:12px; font-weight:600; border:1px solid var(--border);
  background:rgba(14,21,36,.9); color:var(--text); transition:all .2s ease; }
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#22d3ee,#6366f1); color:#061018; border:none;
  box-shadow:0 8px 26px var(--glow); }
.stButton>button:hover{ transform:translateY(-1px); border-color:rgba(34,211,238,.4);
  box-shadow:0 10px 28px var(--glow); }
.stTextArea textarea, .stTextInput input, .stSelectbox [data-baseweb="select"] > div{
  border-radius:12px !important; border-color:var(--border) !important;
  background:rgba(8,14,26,.72) !important; color:var(--text) !important;
  font-family:'IBM Plex Mono',monospace; }
[data-testid="stDataFrame"]{ border-radius:14px; overflow:hidden; border:1px solid var(--border); }
div[data-testid="stAlert"]{ border-radius:12px; border:1px solid var(--border); }
.stRadio > div{ gap:.35rem; }
.section{ font-size:.8rem; text-transform:uppercase; letter-spacing:.12em; color:#67e8f9;
  font-weight:700; margin:18px 0 8px; }
.footer{ text-align:center; color:var(--muted); font-size:.8rem; margin-top:40px; opacity:.7; }

@keyframes fadeUp{ from{opacity:0; transform:translateY(8px);} to{opacity:1; transform:none;} }
@keyframes pulse{ 0%,100%{opacity:.55; transform:scale(1);} 50%{opacity:1; transform:scale(1.06);} }
@keyframes blink{ 0%,100%{opacity:1;} 50%{opacity:.35;} }
</style>
""", unsafe_allow_html=True)

E = html.escape
LABEL = {"ALLOW": "✅ ALLOWED", "REQUIRE_APPROVAL": "⏸️ HUMAN APPROVAL REQUIRED", "BLOCK": "⛔ BLOCKED"}


# --------------------------------------------------------------------------- #
# API helpers
# --------------------------------------------------------------------------- #
def api(method: str, path: str, **kwargs):
    try:
        res = requests.request(method, f"{API_URL}{path}", timeout=kwargs.pop("timeout", 30), **kwargs)
    except requests.RequestException as error:
        st.error(f"Could not reach the backend: {error}")
        return None
    if res.status_code >= 400 and res.status_code != 403:
        st.error(f"API error {res.status_code}: {res.text[:500]}")
        return None
    return res.json()


@st.cache_data(ttl=10, show_spinner=False)
def get_meta():
    return requests.get(f"{API_URL}/meta", timeout=5).json()


def kpi(col, label, value, sub="", color="var(--text)"):
    col.markdown(f'<div class="card"><div class="kpi-label">{E(label)}</div>'
                 f'<div class="kpi-value" style="color:{color}">{E(str(value))}</div>'
                 f'<div class="kpi-sub">{E(sub)}</div></div>', unsafe_allow_html=True)


def badge(text, kind=None):
    return f'<span class="badge b-{E(kind or text)}">{E(str(text))}</span>'


def verdict(decision, reasons):
    st.markdown(f'<div class="verdict v-{E(decision)}"><h2>{LABEL.get(decision, E(decision))}</h2>'
                f'<p>{E(" ".join(reasons))}</p></div>', unsafe_allow_html=True)


def render_timeline(steps):
    parts = ['<div class="timeline">']
    for s in steps:
        fx = "".join(f'<div class="fx">⚠ {E(x)}</div>' for x in s.get("side_effects", []))
        fd = "".join(f'<div class="finding">{badge(f["severity"])} {E(f["message"])}</div>' for f in s.get("findings", []))
        ok = "" if s.get("ok", True) else ' <span class="badge b-BLOCK">FAILS</span>'
        parts.append(
            f'<div class="step s-{E(s["decision"])}"><div class="card">'
            f'<div class="head"><b>Step {s["index"] + 1}</b>{badge(s["tool"], "tool")}{badge(s["decision"])}{ok}</div>'
            f'<div class="summary">{E(s.get("summary", ""))}</div>'
            f'<div class="args">{E(json.dumps(s["arguments"]))}</div>{fd}{fx}</div></div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_impact(impact):
    c = st.columns(6)
    kpi(c[0], "Records read", impact["records_read"])
    kpi(c[1], "Exported", impact["records_exported"], color="var(--approve)" if impact["records_exported"] else "var(--text)")
    kpi(c[2], "Updated", impact["records_updated"])
    kpi(c[3], "Deleted", impact["records_deleted"], f'{impact["records_before"]} → {impact["records_after"]} rows',
        color="var(--block)" if impact["records_deleted"] else "var(--text)")
    kpi(c[4], "External emails", impact["external_emails"], f'{impact["emails_sent"]} total')
    kpi(c[5], "Refund total", f'{impact["refund_total"]:g}')
    flags = []
    if impact["data_left_company"]:
        flags.append('<span class="pill" style="color:var(--block)">🔓 Data leaves company</span>')
    if impact["irreversible"]:
        flags.append('<span class="pill" style="color:var(--approve)">♻️ Irreversible</span>')
    flags.append('<span class="pill" style="color:var(--allow)">🧪 Simulated — real DB untouched</span>')
    st.markdown("<div style='margin-top:12px'>" + "".join(flags) + "</div>", unsafe_allow_html=True)


def render_replay(rep):
    verdict(rep["decision"], rep["reasons"])
    st.markdown('<div class="section">Projected impact</div>', unsafe_allow_html=True)
    render_impact(rep["impact"])
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="section">Step-by-step replay</div>', unsafe_allow_html=True)
        render_timeline(rep["steps"])
    with right:
        st.markdown('<div class="section">Safer alternative</div>', unsafe_allow_html=True)
        safer = rep.get("safer_plan")
        if not safer:
            st.markdown('<div class="card">No changes needed — this plan is already the safest version.</div>',
                        unsafe_allow_html=True)
        else:
            sg = safer["gate"]
            st.markdown(f'<div class="card"><div class="head">Safer plan verdict: {badge(sg["decision"])}</div>'
                        + "".join(f'<div style="margin-top:8px">🔧 {E(c)}</div>' for c in safer["changes"])
                        + "</div>", unsafe_allow_html=True)
            with st.expander("Safer plan JSON"):
                st.code(json.dumps({"actions": safer["actions"]}, indent=2), language="json")


# --------------------------------------------------------------------------- #
# Connection + sidebar
# --------------------------------------------------------------------------- #
try:
    meta = get_meta()
except Exception:
    st.markdown('<div class="hero"><h1>🛡️ ACTION GATE</h1><p>Backend offline.</p></div>', unsafe_allow_html=True)
    st.error(f"Cannot reach the API at {API_URL}. Start it with: `uvicorn app.main:app --reload`")
    if st.button("Retry", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

agent = meta["agent"]
with st.sidebar:
    st.markdown("## 🛡️ ACTION GATE")
    st.caption("AI Agent Security Layer")
    page = st.radio("Navigate", ["📊 Overview", "🤖 Agent Console", "🔁 Consequence Replay",
                                 "⚙️ Direct Execute", "🎯 Red Team", "📜 Audit Log", "📐 Policies"],
                    label_visibility="collapsed")
    st.divider()
    model_txt = f"AMD · {agent['model']}" if agent["model_configured"] else "Mock planner (no AMD key)"
    st.markdown(f'<span class="pill"><span class="dot live"></span>API online</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="pill">🧠 {E(model_txt)}</span>', unsafe_allow_html=True)
    st.caption(f"Endpoint: {API_URL}")
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown(f"""
<div class="hero">
  <span class="pill"><span class="dot live"></span>Live</span>
  <span class="pill">🧠 {E(model_txt)}</span>
  <span class="pill">🔧 {len(meta['tools'])} tools · {len(meta['risk_rules'])} sequence rules</span>
  <h1 style="margin-top:12px">ACTION GATE</h1>
  <p>Every AI agent action is checked, simulated and audited <b>before</b> it runs.</p>
</div>""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
if page == "📊 Overview":
    stats = api("GET", "/audit/stats") or {}
    customers = api("GET", "/customers") or []
    d = stats.get("decisions", {})
    total = stats.get("total", 0)
    c = st.columns(5)
    kpi(c[0], "Decisions logged", total, "all-time")
    kpi(c[1], "Allowed", d.get("ALLOW", 0), f"{(100 * d.get('ALLOW', 0) / total):.0f}%" if total else "—", "var(--allow)")
    kpi(c[2], "Escalated", d.get("REQUIRE_APPROVAL", 0), "needs a human", "var(--approve)")
    kpi(c[3], "Blocked", d.get("BLOCK", 0), "prevented", "var(--block)")
    kpi(c[4], "Customers (sim DB)", len(customers), f"{stats.get('executed', 0)} executions")

    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="section">Decision mix</div>', unsafe_allow_html=True)
        if total:
            st.bar_chart(pd.DataFrame({"count": d}).rename_axis("decision"), color="#22d3ee", height=260)
        else:
            st.info("No decisions yet — try the Agent Console or Red Team.")
    with right:
        st.markdown('<div class="section">Most triggered risk rules</div>', unsafe_allow_html=True)
        if stats.get("top_rules"):
            st.bar_chart(pd.DataFrame({"hits": stats["top_rules"]}).rename_axis("rule"), color="#818cf8",
                         height=260, horizontal=True)
        else:
            st.info("No risk rules triggered yet.")

    st.markdown('<div class="section">Simulated business environment</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(customers), use_container_width=True, hide_index=True)

    st.markdown('<div class="section">Recent activity</div>', unsafe_allow_html=True)
    recent = api("GET", "/audit", params={"limit": 8}) or []
    if recent:
        st.dataframe(pd.DataFrame([{
            "time": e["created_at"], "endpoint": e["endpoint"], "decision": e["decision"],
            "tools": ", ".join(a["tool"] for a in e["actions"]), "instruction": e["instruction"] or "",
        } for e in recent]), use_container_width=True, hide_index=True)

elif page == "🤖 Agent Console":
    st.markdown("### 🤖 Agent Console")
    st.caption("Give the AI agent a task. It proposes a plan → ACTION GATE replays and judges it.")
    examples = meta["example_instructions"]
    picked = st.selectbox("Load a scenario", ["— write your own —"] + examples)
    instruction = st.text_area("Instruction", value="" if picked.startswith("—") else picked,
                               height=100, placeholder="e.g. Refund customer 2 an amount of 120")
    c1, c2, _ = st.columns([1, 1, 3])
    endpoint = None
    if c1.button("🔍 Propose & Replay", use_container_width=True, disabled=not instruction.strip()):
        endpoint = "/agent/propose"
    if c2.button("▶ Run if allowed", type="primary", use_container_width=True, disabled=not instruction.strip()):
        endpoint = "/agent/run"

    if endpoint:
        with st.spinner("Agent is planning, ACTION GATE is replaying consequences…"):
            data = api("POST", endpoint, json={"instruction": instruction}, timeout=120)
        if data:
            st.caption(f"Planner: `{data['source']}` · {len(data['proposed_actions'])} proposed actions")
            if data.get("replay"):
                render_replay(data["replay"])
            else:
                verdict(data["gate"]["decision"], data["gate"]["reasons"])
            if endpoint == "/agent/run":
                st.markdown('<div class="section">Execution</div>', unsafe_allow_html=True)
                if data.get("execution_results"):
                    st.success("Plan was allowed and executed.")
                    st.json(data["execution_results"])
                else:
                    st.warning("Nothing was executed — the gate did not authorize this plan.")
            if data.get("raw_output"):
                with st.expander("Raw model output"):
                    st.code(data["raw_output"])

elif page == "🔁 Consequence Replay":
    st.markdown("### 🔁 Consequence Replay")
    st.caption("Simulate a full multi-step plan against the live data in a rolled-back sandbox. "
               "See every consequence, then get a safer plan.")
    plans = meta["example_plans"]
    choice = st.selectbox("Load a plan from the red-team library", list(plans))
    if st.session_state.get("_loaded_plan") != choice:
        st.session_state["plan_json"] = json.dumps({"actions": plans[choice]}, indent=2)
        st.session_state["_loaded_plan"] = choice

    with st.expander("➕ Add a step with the builder"):
        b1, b2 = st.columns([1, 2])
        tool = b1.selectbox("Tool", meta["tools"] + meta["blocked_tools"])
        args_txt = b2.text_input("Arguments (JSON)", value="{}")
        if st.button("Append step"):
            try:
                plan = json.loads(st.session_state["plan_json"])
                plan.setdefault("actions", []).append({"tool": tool, "arguments": json.loads(args_txt or "{}")})
                st.session_state["plan_json"] = json.dumps(plan, indent=2)
                st.rerun()
            except json.JSONDecodeError as error:
                st.error(f"Invalid JSON: {error}")

    st.text_area("Plan (JSON)", key="plan_json", height=240)
    if st.button("🔁 Run Consequence Replay", type="primary"):
        try:
            plan = json.loads(st.session_state["plan_json"])
            if not isinstance(plan, dict) or not isinstance(plan.get("actions"), list):
                st.error('Plan must be a JSON object with an "actions" list.')
            else:
                with st.spinner("Replaying consequences in sandbox…"):
                    rep = api("POST", "/replay", json=plan)
                if rep:
                    render_replay(rep)
        except json.JSONDecodeError as error:
            st.error(f"Invalid JSON: {error}")

elif page == "⚙️ Direct Execute":
    st.markdown("### ⚙️ Direct Execute")
    agent_tools = set(meta["permissions"].get("ai_agent", []))
    st.caption("The execution layer re-checks permissions independently of the planner. "
               f"The AI agent principal may run: {', '.join(sorted(agent_tools)) or 'nothing'}.")
    customers = api("GET", "/customers") or []
    c1, c2 = st.columns(2)
    tool = c1.selectbox("Tool", meta["tools"])
    arguments: dict = {}
    if tool.startswith("customer.") and tool not in {"customer.list", "customer.export"}:
        if customers:
            options = {f"#{c['id']} · {c['name']} ({c['status']})": c["id"] for c in customers}
            arguments["customer_id"] = options[c2.selectbox("Customer", list(options))]
        else:
            arguments["customer_id"] = int(c2.number_input("Customer ID", min_value=1, step=1))
    extra = st.text_input("Extra arguments (JSON, optional)", value="{}")
    if tool not in agent_tools:
        st.warning(f"`{tool}` is outside the AI agent's permissions — expect a rejection.")
    if st.button("Submit action", type="primary"):
        try:
            arguments.update(json.loads(extra or "{}"))
            res = requests.post(f"{API_URL}/execute", json={"tool": tool, "arguments": arguments}, timeout=10)
            if res.ok:
                verdict("ALLOW", ["Action executed."])
                st.json(res.json())
            else:
                detail = res.json().get("detail", res.text)
                verdict(detail.get("decision", "BLOCK") if isinstance(detail, dict) else "BLOCK",
                        [detail.get("error", "Rejected.") if isinstance(detail, dict) else str(detail)])
                st.json(detail)
        except json.JSONDecodeError as error:
            st.error(f"Invalid JSON: {error}")
        except requests.RequestException as error:
            st.error(f"Could not contact the backend: {error}")

elif page == "🎯 Red Team":
    st.markdown("### 🎯 Red Team Evaluation")
    cases = api("GET", "/redteam/cases") or {}
    n = len(cases.get("instruction_cases", [])) + len(cases.get("plan_cases", []))
    st.caption(f"{n} attacks & controls loaded from data/redteam_cases.json — malicious prompts go through the "
               f"live planner ({model_txt}); unsafe sequences go straight to the gate.")
    if st.button("🚀 Run red-team suite", type="primary"):
        with st.spinner("Attacking ACTION GATE…"):
            st.session_state["redteam"] = api("POST", "/redteam/run", timeout=600)
    rt = st.session_state.get("redteam")
    if rt:
        c = st.columns(5)
        dr, fp = rt["detection_rate"], rt["false_positive_rate"]
        kpi(c[0], "Detection rate", f"{dr}%" if dr is not None else "—", "unsafe cases stopped",
            "var(--allow)" if (dr or 0) >= 90 else "var(--block)")
        kpi(c[1], "False positives", f"{fp}%" if fp is not None else "—", "safe cases stopped",
            "var(--allow)" if (fp or 0) <= 10 else "var(--approve)")
        kpi(c[2], "Blocked", rt["blocked"], color="var(--block)")
        kpi(c[3], "Escalated", rt["escalated"], color="var(--approve)")
        kpi(c[4], "Allowed", rt["allowed"], color="var(--allow)")
        st.markdown('<div class="section">Detection by category</div>', unsafe_allow_html=True)
        cat = pd.DataFrame(rt["by_category"]).T
        cat["rate %"] = (100 * cat["passed"] / cat["total"]).round(1)
        st.bar_chart(cat["rate %"], color="#22d3ee", height=240)
        st.markdown('<div class="section">Case results</div>', unsafe_allow_html=True)
        df = pd.DataFrame(rt["results"])
        df["result"] = df["passed"].map({True: "✅ pass", False: "❌ fail"})
        df["tools"] = df["tools"].apply(lambda t: ", ".join(t))
        st.dataframe(df[["result", "id", "category", "expected", "decision", "input", "tools", "latency_ms", "source"]],
                     use_container_width=True, hide_index=True)

elif page == "📜 Audit Log":
    st.markdown("### 📜 Audit Log")
    c1, c2, c3 = st.columns([1, 1, 1])
    limit = c1.slider("Show last", 10, 500, 100, step=10)
    decisions = c2.multiselect("Decision", ["ALLOW", "REQUIRE_APPROVAL", "BLOCK"],
                               default=["ALLOW", "REQUIRE_APPROVAL", "BLOCK"])
    events = api("GET", "/audit", params={"limit": limit}) or []
    endpoints = sorted({e["endpoint"] for e in events})
    chosen = c3.multiselect("Endpoint", endpoints, default=endpoints)
    rows = [e for e in events if e["decision"] in decisions and e["endpoint"] in chosen]
    if rows:
        st.dataframe(pd.DataFrame([{
            "id": e["id"], "time": e["created_at"], "endpoint": e["endpoint"], "source": e["source"],
            "decision": e["decision"], "executed": e["executed"],
            "tools": ", ".join(a["tool"] for a in e["actions"]),
            "rules": ", ".join(f["rule"] for f in e["findings"]),
            "instruction": e["instruction"] or "",
        } for e in rows]), use_container_width=True, hide_index=True)
        st.download_button("⬇ Export JSON", json.dumps(rows, indent=2), "action_gate_audit.json", "application/json")
    else:
        st.info("No matching audit entries yet.")
    with st.expander("Danger zone"):
        if st.button("Clear audit log"):
            api("DELETE", "/audit")
            st.rerun()

elif page == "📐 Policies":
    st.markdown("### 📐 Active Policies")
    st.caption("Loaded live from the backend. Change thresholds via environment variables (see .env.example).")
    s = meta["settings"]
    c = st.columns(4)
    kpi(c[0], "Refund limit", f'{s["refund_limit"]:g}')
    kpi(c[1], "Bulk delete threshold", s["bulk_delete_threshold"])
    kpi(c[2], "Internal domain", s["internal_email_domain"])
    kpi(c[3], "Export destinations", len(s["approved_export_destinations"]), ", ".join(s["approved_export_destinations"]))

    st.markdown('<div class="section">Sequence risk rules</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"rule": k, **v} for k, v in meta["risk_rules"].items()]),
                 use_container_width=True, hide_index=True)

    st.markdown('<div class="section">Tool policy matrix</div>', unsafe_allow_html=True)
    principals = list(meta["permissions"])
    matrix = []
    for t in meta["tools"] + meta["blocked_tools"]:
        policy = ("BLOCK" if t in meta["blocked_tools"] else
                  "REQUIRE_APPROVAL" if t in meta["approval_required_tools"] else "ALLOW")
        matrix.append({"tool": t, "gate policy": policy,
                       **{p: "✅" if t in meta["permissions"][p] else "—" for p in principals}})
    st.dataframe(pd.DataFrame(matrix), use_container_width=True, hide_index=True)

version = (api("GET", "/") or {}).get("version", "")
st.markdown(f'<div class="footer">ACTION GATE v{E(str(version))} · AMD Developer Hackathon · '
            f'Security decisions before action execution</div>', unsafe_allow_html=True)

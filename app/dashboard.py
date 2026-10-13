
import json

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ACTION GATE",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ ACTION GATE")
st.caption("A security gateway for AI agent actions")
st.divider()

# Check whether the backend is running.
try:
    response = requests.get(f"{API_URL}/", timeout=3)
    backend_online = response.status_code == 200
except requests.RequestException:
    backend_online = False

if backend_online:
    st.success("Backend connected")
else:
    st.error(
        "Backend is offline. Start FastAPI in another terminal "
        "using: uvicorn app.main:app --reload"
    )
    st.stop()

tab_evaluate, tab_execute = st.tabs(
    ["🔍 Evaluate Plan", "⚙️ Execute Action"]
)

with tab_evaluate:
    st.subheader("Plan Security Analysis")
    st.write(
        "Submit a sequence of proposed actions. "
        "ACTION GATE will evaluate policies and detect risky sequences."
    )

    default_plan = {
        "actions": [
            {
                "tool": "customer.read",
                "arguments": {"customer_id": 1},
            }
        ]
    }

    plan_text = st.text_area(
        "Action plan (JSON)",
        value=json.dumps(default_plan, indent=2),
        height=260,
        key="plan_input",
    )

    if st.button("Evaluate Plan", type="primary"):
        try:
            plan = json.loads(plan_text)

            if not isinstance(plan, dict) or not isinstance(
                plan.get("actions"), list
            ):
                st.error(
                    'Enter a JSON object containing an "actions" list.'
                )
            else:
                result = requests.post(
                    f"{API_URL}/evaluate",
                    json=plan,
                    timeout=10,
                )

                if result.ok:
                    data = result.json()
                    decision = data.get("decision", "UNKNOWN")

                    if decision == "ALLOW":
                        st.success(f"Decision: {decision}")
                    elif decision == "REQUIRE_APPROVAL":
                        st.warning(f"Decision: {decision}")
                    else:
                        st.error(f"Decision: {decision}")

                    st.subheader("Decision Summary")
                    st.write("**Reasons**")
                    st.write(data.get("reasons", []))

                    st.subheader("Individual Action Decisions")
                    st.json(data.get("action_decisions", []))

                    st.subheader("Consequence Replay Findings")
                    findings = data.get("risk_findings", [])

                    if findings:
                        for finding in findings:
                            severity = finding.get("severity", "UNKNOWN")
                            st.warning(
                                f"{severity}: {finding.get('message', '')}"
                            )
                        st.json(findings)
                    else:
                        st.info("No sequence-level risks detected.")

                    st.write(
                        "**Execution authorized by plan evaluator:**",
                        data.get("execution_authorized", False),
                    )
                else:
                    st.error(f"API error ({result.status_code})")
                    st.code(result.text)

        except json.JSONDecodeError as error:
            st.error(f"Invalid JSON: {error}")
        except requests.RequestException as error:
            st.error(f"Could not contact the backend: {error}")

with tab_execute:
    st.subheader("Execute a Permitted Action")
    st.write(
        "The backend independently checks permissions before "
        "executing an action. The AI agent has read-only access."
    )

    tool = st.selectbox(
        "Select a tool",
        ["customer.list", "customer.read", "customer.delete"],
    )

    arguments = {}

    if tool in {"customer.read", "customer.delete"}:
        customer_id = st.number_input(
            "Customer ID",
            min_value=1,
            value=1,
            step=1,
        )
        arguments["customer_id"] = int(customer_id)

    if tool == "customer.delete":
        st.warning(
            "The AI agent is not permitted to delete customers. "
            "This request should be rejected."
        )

    if st.button("Submit Action"):
        try:
            action = {
                "tool": tool,
                "arguments": arguments,
                "actor": "ai_agent",
            }

            result = requests.post(
                f"{API_URL}/execute",
                json=action,
                timeout=10,
            )

            if result.ok:
                st.success("Action executed successfully")
                st.json(result.json())
            elif result.status_code == 403:
                st.error("Action rejected by the security layer")
                st.json(result.json())
            else:
                st.error(f"API error ({result.status_code})")
                st.code(result.text)

        except requests.RequestException as error:
            st.error(f"Could not contact the backend: {error})s")

st.divider()
st.caption("ACTION GATE • Security decisions before action execution")

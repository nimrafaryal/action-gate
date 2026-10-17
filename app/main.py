
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import config, redteam
from app.schemas import ActionRequest
from app.gate.controller import evaluate_plan
from app.gate.policy_engine import APPROVAL_REQUIRED_TOOLS, BLOCKED_TOOLS, KNOWN_TOOLS
from app.gate.replay import consequence_replay
from app.gate.risk_analyzer import RISK_RULES
from app.storage import audit
from app.storage.database import get_customers
from app.tools.registry import TOOL_PERMISSIONS, execute_action
from app.agent import llm_client
from app.agent.planner import PlanParseError, propose_plan
from app.gate.instruction_guard import detect_instruction_attack

app = FastAPI(
    title="ACTION GATE",
    description="A security layer for AI agent actions.",
    version="0.2.0",
)


class PlanRequest(BaseModel):
    actions: list[ActionRequest] = Field(max_length=50)


@app.get("/")
def home():
    return {
        "project": "ACTION GATE",
        "status": "running",
        "version": app.version,
        "message": "AI action security gateway is online.",
    }


@app.get("/meta")
def meta():
    """Everything the dashboard needs to render itself — no hard-coded UI data."""
    cases = redteam.load_cases()
    return {
        "tools": sorted(KNOWN_TOOLS),
        "approval_required_tools": sorted(APPROVAL_REQUIRED_TOOLS),
        "blocked_tools": sorted(BLOCKED_TOOLS),
        "permissions": {p: sorted(t) for p, t in TOOL_PERMISSIONS.items()},
        "risk_rules": RISK_RULES,
        "settings": {
            "refund_limit": config.REFUND_LIMIT,
            "bulk_delete_threshold": config.BULK_DELETE_THRESHOLD,
            "internal_email_domain": config.INTERNAL_EMAIL_DOMAIN,
            "approved_export_destinations": sorted(config.APPROVED_EXPORT_DESTINATIONS),
        },
        "example_instructions": [c["instruction"] for c in cases.get("instruction_cases", [])],
        "example_plans": {c["id"]: c["actions"] for c in cases.get("plan_cases", [])},
        "agent": agent_status(),
    }


@app.get("/customers")
def customers():
    return get_customers()


@app.post("/evaluate")
def evaluate(request: PlanRequest):
    result = evaluate_plan(request.actions)
    audit.log_event("/evaluate", request.actions, result, source="manual")
    return result


@app.post("/replay")
def replay(request: PlanRequest):
    """Consequence Replay: simulate the full plan and suggest a safer one."""
    result = consequence_replay(request.actions)
    audit.log_event("/replay", request.actions, result, source="manual")
    return result



@app.post("/execute")
def execute(action: ActionRequest):
    """Execute one action only when all gate checks authorize it."""
    plan_gate = evaluate_plan([action])

    if not plan_gate["execution_authorized"]:
        audit.log_event(
            "/execute",
            [action],
            plan_gate,
            source="manual",
            executed=False,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Security gate denied execution.",
                "gate": plan_gate,
            },
        )

    result = execute_action(action, principal="ai_agent")

    gate = {
        "decision": "ALLOW" if result.get("success") else result.get("decision", "BLOCK"),
        "reasons": [result.get("error")] if result.get("error") else ["Executed."],
        "execution_authorized": bool(result.get("success")),
    }

    audit.log_event(
        "/execute",
        [action],
        gate,
        source="manual",
        executed=bool(result.get("success")),
    )

    if not result.get("success"):
        raise HTTPException(status_code=403, detail=result)

    return result



@app.get("/audit")
def audit_log(limit: int = 100):
    return audit.list_events(min(max(limit, 1), 1000))


@app.get("/audit/stats")
def audit_stats():
    return audit.stats()


@app.delete("/audit")
def audit_clear():
    audit.clear()
    return {"cleared": True}


@app.get("/redteam/cases")
def redteam_cases():
    return redteam.load_cases()


@app.post("/redteam/run")
def redteam_run():
    return redteam.run_suite()


class AgentRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)


def _propose_and_gate(instruction: str) -> dict:
        # Check the original instruction before trusting the model's plan.
    instruction_findings = detect_instruction_attack(instruction)

    if instruction_findings:
        return {
            "source": "instruction_guard",
            "proposed_actions": [],
            "instruction_findings": instruction_findings,
            "gate": {
                "decision": "BLOCK",
                "reasons": [
                    "The instruction contains a suspected security override attempt."
                ],
                "action_decisions": [],
                "risk_findings": [
                    {
                        "rule": rule,
                        "severity": "HIGH",
                        "message": "Suspicious instruction override detected.",
                    }
                    for rule in instruction_findings
                ],
                "execution_authorized": False,
            },
        }
    try:
        proposal = propose_plan(instruction)
    except PlanParseError as error:
        # Unparseable / malformed model output is never executed.
        return {
            "source": "amd",
            "proposed_actions": [],
            "gate": {
                "decision": "BLOCK",
                "reasons": [f"Model output rejected: {error}"],
                "action_decisions": [],
                "risk_findings": [],
                "execution_authorized": False,
            },
        }
    except Exception as error:  # network / API failure
        raise HTTPException(status_code=502, detail=f"Model call failed: {error}")

    actions = proposal["actions"]
    return {
        "source": proposal["source"],
        "raw_output": proposal["raw_output"],
        "proposed_actions": [a.model_dump() for a in actions],
        "gate": evaluate_plan(actions),
        "_actions": actions,
    }


@app.get("/agent/status")
def agent_status():
    cfg = llm_client.get_config()
    return {"model_configured": llm_client.is_configured(), "model": cfg["model"] or "mock"}


@app.post("/agent/propose")
def agent_propose(request: AgentRequest):
    """The AI proposes a plan; ACTION GATE evaluates it. Nothing executes."""
    result = _propose_and_gate(request.instruction)
    actions = result.pop("_actions", [])
    if actions:
        result["replay"] = consequence_replay(actions)
    audit.log_event("/agent/propose", actions, result["gate"],
                    source=result["source"], instruction=request.instruction)
    return result


@app.post("/agent/run")
def agent_run(request: AgentRequest):
    """Propose, evaluate, and execute ONLY if the full plan is ALLOWed."""
    result = _propose_and_gate(request.instruction)
    actions = result.pop("_actions", [])
    if actions:
        result["replay"] = consequence_replay(actions)

    if result["gate"]["execution_authorized"]:
        result["execution_results"] = [
            execute_action(action, principal="ai_agent") for action in actions
        ]
    else:
        result["execution_results"] = []
    audit.log_event("/agent/run", actions, result["gate"], source=result["source"],
                    instruction=request.instruction,
                    executed=bool(result["execution_results"]))
    return result

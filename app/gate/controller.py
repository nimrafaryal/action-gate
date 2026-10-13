
from app.schemas import ActionRequest
from app.gate.policy_engine import evaluate_action
from app.gate.risk_analyzer import analyze_sequence


def evaluate_plan(actions: list[ActionRequest]) -> dict:
    """Evaluate an entire plan before any tool can execute."""
    
    if not actions:
        return {
            "decision": "BLOCK","reasons": ["Empty plans are not accepted."],
            "action_decisions": [],
            "risk_findings": [],
            "execution_authorized": False,
    }

    # Check each action against the individual security policies.
    action_decisions = [
        evaluate_action(action).model_dump()
        for action in actions
    ]

    # Check the complete plan for dangerous action combinations.
    risk_findings = analyze_sequence(actions)

    reasons = []
    decision = "ALLOW"

    # A single prohibited action blocks the entire plan.
    if any(item["decision"] == "BLOCK" for item in action_decisions):
        decision = "BLOCK"
        reasons.append("At least one action violates a security policy.")

    # Certain sequence-level risks require blocking.
    blocking_rules = {
        "unapproved_export_destination",
        "export_send_delete_sequence",
    }

    if any(
        finding["rule"] in blocking_rules
        for finding in risk_findings
    ):
        decision = "BLOCK"
        reasons.append("The plan contains a prohibited risk pattern.")

    # Approval is required if the plan is not already blocked.
    approval_needed = any(
        item["decision"] == "REQUIRE_APPROVAL"
        for item in action_decisions
    ) or any(
        finding["rule"] == "bulk_deletion"
        for finding in risk_findings
    )

    if decision != "BLOCK" and approval_needed:
        decision = "REQUIRE_APPROVAL"
        reasons.append("Human approval is required.")

    if decision == "ALLOW":
        reasons.append("All current policy and sequence checks passed.")

    return {
        "decision": decision,
        "reasons": reasons,
        "action_decisions": action_decisions,
        "risk_findings": risk_findings,
        "execution_authorized": decision == "ALLOW",
    }

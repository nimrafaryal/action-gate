
from app.schemas import ActionRequest, GateDecision, PolicyCheck


# Tools the agent is permitted to request.
KNOWN_TOOLS = {
    "customer.list",
    "customer.read",
    "customer.update",
    "customer.delete",
    "customer.export",
    "refund.process",
    "email.send",
}

# Actions that always need human review in this first version.
APPROVAL_REQUIRED_TOOLS = {
    "customer.delete",
    "customer.export",
    "refund.process",
    "email.send",
}

# Tools the agent is never permitted to execute.
BLOCKED_TOOLS = {
    "permission.change",
    "system.execute",
}


def evaluate_action(action: ActionRequest) -> GateDecision:
    """Apply deterministic rules to a proposed action."""

    checks = []
    reasons = []

    # Policy 1: deny unknown tools.
    known = action.tool in KNOWN_TOOLS
    checks.append(
        PolicyCheck(
            policy="known_tool",
            passed=known,
            reason=(
                "Tool is registered."
                if known
                else "Unknown tools are denied by default."
            ),
        )
    )

    if not known:
        return GateDecision(
            action_id="pending",
            decision="BLOCK",
            reasons=["Unknown tool."],
            policy_checks=checks,
        )

    # Policy 2: block explicitly forbidden tools.
    forbidden = action.tool in BLOCKED_TOOLS
    checks.append(
        PolicyCheck(
            policy="forbidden_tool",
            passed=not forbidden,
            reason=(
                "Tool is not explicitly forbidden."
                if not forbidden
                else "This tool is prohibited by security policy."
            ),
        )
    )

    if forbidden:
        return GateDecision(
            action_id="pending",
            decision="BLOCK",
            reasons=["Tool is explicitly forbidden."],
            policy_checks=checks,
        )

    # Policy 3: require review for sensitive actions.
    needs_approval = action.tool in APPROVAL_REQUIRED_TOOLS
    checks.append(
        PolicyCheck(
            policy="human_approval",
            passed=not needs_approval,
            reason=(
                "No approval required by this policy."
                if not needs_approval
                else "Sensitive action requires human approval."
            ),
        )
    )

    if needs_approval:
        return GateDecision(
            action_id="pending",
            decision="REQUIRE_APPROVAL",
            reasons=["Human approval is required."],
            policy_checks=checks,
        )

    # Only registered, non-sensitive actions are allowed by these
    # initial rules. Further permission checks will be added next.
    return GateDecision(
        action_id="pending",
        decision="ALLOW",
        reasons=["Action passed the initial policy checks."],
        policy_checks=checks,
    )

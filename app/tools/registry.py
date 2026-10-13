
from app.schemas import ActionRequest
from app.gate.policy_engine import evaluate_action
from app.storage.database import get_customers


# Permissions are assigned by the application, not by the AI agent.
TOOL_PERMISSIONS = {
    "ai_agent": {
        "customer.list",
        "customer.read",
    },
    "admin": {
        "customer.list",
        "customer.read",
        "customer.update",
        "customer.delete",
    },
}


def execute_action(
    action: ActionRequest,
    principal: str = "ai_agent",
) -> dict:
    """
    Execute an action only when the principal has permission
    and the security gate allows the action.
    """

    # 1. Check the principal's independent permissions.
    allowed_tools = TOOL_PERMISSIONS.get(principal, set())

    if action.tool not in allowed_tools:
        return {
            "success": False,
            "error": "Permission denied for this principal.",
            "tool": action.tool,
        }

    # 2. Check the security gate before execution.
    decision = evaluate_action(action)

    if decision.decision != "ALLOW":
        return {
            "success": False,
            "error": "Security gate denied execution.",
            "decision": decision.decision,
            "reasons": decision.reasons,
            "tool": action.tool,
        }

    # 3. Execute only registered handlers.
    if action.tool == "customer.list":
        return {
            "success": True,
            "tool": action.tool,
            "result": get_customers(),
        }

    if action.tool == "customer.read":
        customer_id = action.arguments.get("customer_id")

        if not isinstance(customer_id, int) or isinstance(customer_id, bool):
            return {
                "success": False,
                "error": "customer_id must be an integer.",
            }

        customers = get_customers()
        customer = next(
            (item for item in customers if item["id"] == customer_id),
            None,
        )

        if customer is None:
            return {
                "success": False,
                "error": f"Customer {customer_id} does not exist.",
            }

        return {
            "success": True,
            "tool": action.tool,
            "result": customer,
        }

    return {
        "success": False,
        "error": "No execution handler is registered for this tool.",
        "tool": action.tool,
    }

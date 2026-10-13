
from app.schemas import ActionRequest
from app.tools.registry import execute_action


def test_ai_agent_can_read_customer():
    action = ActionRequest(
        tool="customer.read",
        arguments={"customer_id": 1},
    )

    result = execute_action(action)

    assert result["success"] is True
    assert result["result"]["id"] == 1


def test_ai_agent_cannot_delete_customer():
    action = ActionRequest(
        tool="customer.delete",
        arguments={"customer_id": 1},
    )

    result = execute_action(action)

    assert result["success"] is False
    assert "Permission denied" in result["error"]


def test_unknown_principal_has_no_permissions():
    action = ActionRequest(tool="customer.list")

    result = execute_action(action, principal="unknown_user")

    assert result["success"] is False
    assert "Permission denied" in result["error"]


def test_unknown_tool_cannot_execute():
    action = ActionRequest(tool="customer.steal_all_data")

    result = execute_action(action)

    assert result["success"] is False


from app.schemas import ActionRequest
from app.gate.policy_engine import evaluate_action


def test_customer_read_is_allowed():
    action = ActionRequest(
        tool="customer.read",
        arguments={"customer_id": 1},
    )

    decision = evaluate_action(action)

    assert decision.decision == "ALLOW"


def test_customer_delete_requires_approval():
    action = ActionRequest(
        tool="customer.delete",
        arguments={"customer_id": 1},
    )

    decision = evaluate_action(action)

    assert decision.decision == "REQUIRE_APPROVAL"


def test_unknown_tool_is_blocked():
    action = ActionRequest(
        tool="customer.steal_all_data",
        arguments={},
    )

    decision = evaluate_action(action)

    assert decision.decision == "BLOCK"


def test_permission_change_is_blocked():
    action = ActionRequest(
        tool="permission.change",
        arguments={"role": "admin"},
    )

    decision = evaluate_action(action)

    assert decision.decision == "BLOCK"

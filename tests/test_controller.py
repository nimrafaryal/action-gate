
from app.schemas import ActionRequest
from app.gate.controller import evaluate_plan


def test_safe_read_plan_is_allowed():
    actions = [
        ActionRequest(
            tool="customer.read",
            arguments={"customer_id": 1},
        ),
        ActionRequest(
            tool="customer.read",
            arguments={"customer_id": 2},
        ),
    ]

    result = evaluate_plan(actions)

    assert result["decision"] == "ALLOW"
    assert result["execution_authorized"] is True


def test_sensitive_delete_requires_approval():
    actions = [
        ActionRequest(
            tool="customer.delete",
            arguments={"customer_id": 1},
        )
    ]

    result = evaluate_plan(actions)

    assert result["decision"] == "REQUIRE_APPROVAL"
    assert result["execution_authorized"] is False


def test_dangerous_sequence_blocks_entire_plan():
    actions = [
        ActionRequest(
            tool="customer.export",
            arguments={"destination": "external_server"},
        ),
        ActionRequest(
            tool="email.send",
            arguments={"recipient": "external@example.com"},
        ),
        ActionRequest(
            tool="customer.delete",
            arguments={"customer_id": 1},
        ),
    ]

    result = evaluate_plan(actions)

    assert result["decision"] == "BLOCK"
    assert result["execution_authorized"] is False
    assert result["risk_findings"]


def test_unknown_tool_blocks_entire_plan():
    actions = [
        ActionRequest(
            tool="customer.read",
            arguments={"customer_id": 1},
        ),
        ActionRequest(
            tool="customer.unknown",
            arguments={},
        ),
    ]

    result = evaluate_plan(actions)

    assert result["decision"] == "BLOCK"
    assert result["execution_authorized"] is False


def test_empty_plan_is_blocked():
    result = evaluate_plan([])

    assert result["decision"] == "BLOCK"
    assert result["execution_authorized"] is False

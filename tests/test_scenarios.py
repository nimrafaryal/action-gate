
from app.schemas import ActionRequest
from app.gate.risk_analyzer import analyze_sequence


def test_export_to_unapproved_destination_is_flagged():
    actions = [
        ActionRequest(
            tool="customer.export",
            arguments={"destination": "external_server"},
        )
    ]

    findings = analyze_sequence(actions)

    assert any(
        finding["rule"] == "unapproved_export_destination"
        for finding in findings
    )


def test_export_send_delete_sequence_is_flagged():
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

    findings = analyze_sequence(actions)

    assert any(
        finding["rule"] == "export_send_delete_sequence"
        for finding in findings
    )


def test_safe_internal_export_is_not_flagged():
    actions = [
        ActionRequest(
            tool="customer.export",
            arguments={"destination": "internal_review"},
        )
    ]

    findings = analyze_sequence(actions)

    assert findings == []


def test_bulk_deletion_requires_review():
    actions = [
        ActionRequest(
            tool="customer.delete",
            arguments={"customer_id": customer_id},
        )
        for customer_id in [1, 2, 3]
    ]

    findings = analyze_sequence(actions)

    assert any(
        finding["rule"] == "bulk_deletion"
        for finding in findings
    )


def test_harmless_read_plan_has_no_findings():
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

    assert analyze_sequence(actions) == []

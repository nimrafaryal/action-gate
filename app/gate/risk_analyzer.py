
from app import config
from app.schemas import ActionRequest


APPROVED_EXPORT_DESTINATIONS = config.APPROVED_EXPORT_DESTINATIONS

# Human-readable catalogue of sequence rules (served to the dashboard).
RISK_RULES = {
    "unapproved_export_destination": {"severity": "HIGH", "effect": "BLOCK",
        "description": "Customer data exported to a destination outside the approved list."},
    "export_send_delete_sequence": {"severity": "CRITICAL", "effect": "BLOCK",
        "description": "Unapproved export, then email, then deletion of the source records."},
    "bulk_deletion": {"severity": "HIGH", "effect": "REQUIRE_APPROVAL",
        "description": f"{config.BULK_DELETE_THRESHOLD}+ deletions in a single plan."},
    "large_refund": {"severity": "HIGH", "effect": "REQUIRE_APPROVAL",
        "description": f"Refund above the {config.REFUND_LIMIT:g} limit."},
    "contact_email_change": {"severity": "HIGH", "effect": "REQUIRE_APPROVAL",
        "description": "Changing a customer's contact email (account-takeover vector)."},
}


def analyze_sequence(actions: list[ActionRequest]) -> list[dict]:
    """
    Inspect a complete action plan for dangerous combinations.

    This analyzer reports risks. The policy engine and execution
    controller remain responsible for enforcing the decision.
    """
    findings = []

    tools = [action.tool for action in actions]

    # Rule 1: exporting customer data to an unapproved destination.
    for index, action in enumerate(actions):
        if action.tool == "customer.export":
            destination = action.arguments.get("destination")

            if destination not in APPROVED_EXPORT_DESTINATIONS:
                findings.append({
                    "rule": "unapproved_export_destination",
                    "severity": "HIGH",
                    "action_index": index,
                    "message": (
                        "Customer data export targets an unapproved "
                        "destination."
                    ),
                })

    # Rule 2: sending customer data externally and then deleting
    # the source records within the same plan.
    export_positions = [
        i for i, tool in enumerate(tools)
        if tool == "customer.export"
    ]

    send_positions = [
        i for i, tool in enumerate(tools)
        if tool == "email.send"
    ]

    delete_positions = [
        i for i, tool in enumerate(tools)
        if tool == "customer.delete"
    ]

    for export_index in export_positions:
        export_destination = actions[export_index].arguments.get(
            "destination"
        )

        if export_destination in APPROVED_EXPORT_DESTINATIONS:
            continue

        for send_index in send_positions:
            if send_index < export_index:
                continue

            for delete_index in delete_positions:
                if delete_index > send_index:
                    findings.append({
                        "rule": "export_send_delete_sequence",
                        "severity": "CRITICAL",
                        "action_index": delete_index,
                        "message": (
                            "The plan combines an unapproved customer "
                            "export, an email operation, and subsequent "
                            "source-record deletion."
                        ),
                    })

    # Rule 3: bulk deletion requires special review.
    if len(delete_positions) >= config.BULK_DELETE_THRESHOLD:
        findings.append({
            "rule": "bulk_deletion",
            "severity": "HIGH",
            "action_index": delete_positions[0],
            "message": (
                f"The plan contains {len(delete_positions)} deletion actions "
                f"(threshold {config.BULK_DELETE_THRESHOLD}) and requires human review."
            ),
        })

    # Rule 4: unusually large refunds.
    for index, action in enumerate(actions):
        if action.tool != "refund.process":
            continue
        amount = action.arguments.get("amount")
        if isinstance(amount, (int, float)) and not isinstance(amount, bool) \
                and amount > config.REFUND_LIMIT:
            findings.append({
                "rule": "large_refund",
                "severity": "HIGH",
                "action_index": index,
                "message": (
                    f"Refund of {amount:g} exceeds the {config.REFUND_LIMIT:g} limit."
                ),
            })

    # Rule 5: contact email changes enable account takeover.
    for index, action in enumerate(actions):
        if action.tool == "customer.update" and action.arguments.get("field") == "email":
            findings.append({
                "rule": "contact_email_change",
                "severity": "HIGH",
                "action_index": index,
                "message": (
                    f"Changes customer #{action.arguments.get('customer_id')} "
                    f"email to '{action.arguments.get('value')}'."
                ),
            })

    return findings

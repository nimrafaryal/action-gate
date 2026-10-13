
from app.schemas import ActionRequest


APPROVED_EXPORT_DESTINATIONS = {
    "internal_review"
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
    if len(delete_positions) >= 3:
        findings.append({
            "rule": "bulk_deletion",
            "severity": "HIGH",
            "action_index": delete_positions[0],
            "message": (
                "The plan contains three or more deletion actions "
                "and requires human review."
            ),
        })

    return findings

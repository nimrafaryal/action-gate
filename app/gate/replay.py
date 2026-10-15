"""
Consequence Replay — simulate an entire multi-step plan before it runs.

Every step is replayed against the real SQLite data inside a transaction
that is always rolled back, so the real database is never modified.
Non-database tools (export, email, refund) are simulated from live data.
The replay reports per-step consequences, an aggregate impact summary,
and a safer alternative plan that is itself re-evaluated by the gate.
"""

import sqlite3

from app import config
from app.gate.controller import evaluate_plan
from app.schemas import ActionRequest
from app.storage.database import DATABASE_PATH, initialize_database


def _snapshot(connection) -> dict[int, dict]:
    rows = connection.execute(
        "SELECT id, name, email, status FROM customers ORDER BY id"
    ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def _valid_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _simulate_step(connection, action: ActionRequest, state: dict) -> dict:
    """Apply one action inside the open transaction and describe its effect."""
    args = action.arguments
    tool = action.tool
    side_effects: list[str] = []
    effect: dict = {"ok": True}

    if tool == "customer.list":
        count = len(_snapshot(connection))
        effect["summary"] = f"Reads {count} customer records."
        state["records_read"] += count

    elif tool == "customer.read":
        cid = args.get("customer_id")
        row = _snapshot(connection).get(cid) if _valid_id(cid) else None
        if row:
            effect["summary"] = f"Reads customer #{cid} ({row['name']})."
            state["records_read"] += 1
        else:
            effect.update(ok=False, summary=f"Customer {cid!r} does not exist.")

    elif tool == "customer.update":
        cid, field, value = args.get("customer_id"), args.get("field"), args.get("value")
        if not _valid_id(cid) or field not in {"email", "status"} or not isinstance(value, str):
            effect.update(ok=False, summary="Invalid update arguments.")
        else:
            cur = connection.execute(
                f"UPDATE customers SET {field} = ? WHERE id = ?", (value, cid)
            )
            if cur.rowcount:
                effect["summary"] = f"Sets {field} of customer #{cid} to '{value}'."
                state["records_updated"].add(cid)
                if field == "email":
                    side_effects.append("Customer contact email changes — possible account takeover vector.")
            else:
                effect.update(ok=False, summary=f"Customer {cid} does not exist.")

    elif tool == "customer.delete":
        cid = args.get("customer_id")
        cur = connection.execute("DELETE FROM customers WHERE id = ?", (cid,)) if _valid_id(cid) else None
        if cur is not None and cur.rowcount:
            effect["summary"] = f"Permanently deletes customer #{cid}."
            state["records_deleted"].add(cid)
            side_effects.append("Irreversible data loss.")
            if state["data_left_company"]:
                side_effects.append("Deletes source records after data already left the company — evidence destruction pattern.")
        else:
            effect.update(ok=False, summary=f"Customer {cid!r} does not exist.")

    elif tool == "customer.export":
        dest = args.get("destination")
        count = len(_snapshot(connection))
        approved = dest in config.APPROVED_EXPORT_DESTINATIONS
        effect["summary"] = f"Exports {count} customer records to '{dest}'."
        state["records_exported"] += count
        state["exported"] = True
        if not approved:
            state["data_left_company"] = True
            side_effects.append(f"{count} records of personal data leave the approved boundary.")

    elif tool == "email.send":
        to = args.get("to") or args.get("recipient")
        internal = config.is_internal_email(to)
        effect["summary"] = f"Sends an email to {to or 'an unspecified recipient'}."
        state["emails_sent"] += 1
        if not internal:
            state["external_emails"] += 1
            if state["exported"]:
                state["data_left_company"] = True
                side_effects.append("Exported customer data may be attached to an external email.")

    elif tool == "refund.process":
        cid, amount = args.get("customer_id"), args.get("amount")
        if not _valid_id(cid) or not isinstance(amount, (int, float)) or amount <= 0:
            effect.update(ok=False, summary="Invalid refund arguments.")
        else:
            exists = cid in _snapshot(connection)
            effect["summary"] = f"Refunds {amount:g} to customer #{cid}."
            state["refund_total"] += amount
            if not exists:
                side_effects.append("Refund targets a customer that does not exist — likely fraud.")
            if amount > config.REFUND_LIMIT:
                side_effects.append(f"Exceeds refund limit of {config.REFUND_LIMIT:g}.")

    else:
        effect.update(ok=False, summary=f"No simulator for '{tool}'.")
        side_effects.append("Unknown capability — cannot predict consequences.")

    effect["side_effects"] = side_effects
    return effect


def suggest_safer_plan(actions: list[ActionRequest], gate: dict) -> tuple[list[ActionRequest], list[str]]:
    """Rewrite a plan into the closest lower-risk equivalent."""
    safer: list[ActionRequest] = []
    changes: list[str] = []
    exported_externally = False
    fallback_dest = sorted(config.APPROVED_EXPORT_DESTINATIONS)[0] if config.APPROVED_EXPORT_DESTINATIONS else None

    for index, action in enumerate(actions):
        per_action = gate["action_decisions"][index]["decision"] if index < len(gate["action_decisions"]) else "BLOCK"
        args = dict(action.arguments)

        if per_action == "BLOCK":
            changes.append(f"Step {index + 1}: removed '{action.tool}' (prohibited).")
            continue

        if action.tool == "customer.export" and args.get("destination") not in config.APPROVED_EXPORT_DESTINATIONS:
            exported_externally = True
            if fallback_dest:
                changes.append(f"Step {index + 1}: export redirected from '{args.get('destination')}' to '{fallback_dest}'.")
                args["destination"] = fallback_dest
            else:
                changes.append(f"Step {index + 1}: removed export (no approved destination).")
                continue

        if action.tool == "email.send" and not config.is_internal_email(args.get("to") or args.get("recipient")):
            if exported_externally or any(a.tool == "customer.export" for a in actions[:index]):
                changes.append(f"Step {index + 1}: removed external email that could carry exported data.")
                continue

        if action.tool == "customer.delete":
            changes.append(f"Step {index + 1}: hard delete of #{args.get('customer_id')} replaced with reversible deactivation.")
            safer.append(ActionRequest(tool="customer.update", actor=action.actor,
                                       arguments={"customer_id": args.get("customer_id"), "field": "status", "value": "inactive"}))
            continue

        if action.tool == "refund.process" and isinstance(args.get("amount"), (int, float)) \
                and args["amount"] > config.REFUND_LIMIT:
            changes.append(f"Step {index + 1}: refund capped from {args['amount']:g} to {config.REFUND_LIMIT:g}.")
            args["amount"] = config.REFUND_LIMIT

        safer.append(ActionRequest(tool=action.tool, arguments=args, actor=action.actor))

    return safer, changes


def consequence_replay(actions: list[ActionRequest]) -> dict:
    """Simulate the full plan, gate it, and propose a safer alternative."""
    gate = evaluate_plan(actions)
    initialize_database()

    state = {
        "records_read": 0, "records_exported": 0, "records_updated": set(),
        "records_deleted": set(), "emails_sent": 0, "external_emails": 0,
        "refund_total": 0.0, "exported": False, "data_left_company": False,
    }
    steps = []

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN")
        before = _snapshot(connection)
        for index, action in enumerate(actions):
            effect = _simulate_step(connection, action, state)
            decision = gate["action_decisions"][index]
            steps.append({
                "index": index,
                "tool": action.tool,
                "arguments": action.arguments,
                "decision": decision["decision"],
                "reasons": decision["reasons"],
                "findings": [f for f in gate["risk_findings"] if f.get("action_index") == index],
                **effect,
            })
        after = _snapshot(connection)
    finally:
        connection.rollback()
        connection.close()

    impact = {
        "records_before": len(before),
        "records_after": len(after),
        "records_read": state["records_read"],
        "records_exported": state["records_exported"],
        "records_updated": len(state["records_updated"]),
        "records_deleted": len(state["records_deleted"]),
        "emails_sent": state["emails_sent"],
        "external_emails": state["external_emails"],
        "refund_total": state["refund_total"],
        "data_left_company": state["data_left_company"],
        "irreversible": bool(state["records_deleted"]) or state["data_left_company"],
        "real_database_modified": False,
    }

    safer_actions, changes = suggest_safer_plan(actions, gate)
    safer = None
    if changes:
        safer = {
            "actions": [a.model_dump() for a in safer_actions],
            "changes": changes,
            "gate": evaluate_plan(safer_actions),
        }

    return {**gate, "steps": steps, "impact": impact, "safer_plan": safer}

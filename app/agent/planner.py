"""
AI planner: turns a natural-language instruction into a structured
action plan. The planner only PROPOSES actions — ACTION GATE decides.

If the AMD model is not configured (e.g. credits not approved yet), a
deterministic mock planner is used so the demo and tests still work.
"""

import json
import re

from pydantic import ValidationError

from app.agent import llm_client
from app.gate.policy_engine import KNOWN_TOOLS
from app.schemas import ActionRequest

MAX_ACTIONS = 20

SYSTEM_PROMPT = f"""You are a business operations AI agent for a simulated company.
You can ONLY propose actions; a security layer will review them before execution.

Available tools and arguments:
- customer.list {{}}
- customer.read {{"customer_id": int}}
- customer.update {{"customer_id": int, "field": "email"|"status", "value": str}}
- customer.delete {{"customer_id": int}}
- customer.export {{"destination": str}}  (company-approved destination: "internal_review")
- refund.process {{"customer_id": int, "amount": number}}
- email.send {{"to": str, "subject": str, "body": str}}

Respond with ONLY a JSON object, no prose, in this exact format:
{{"actions": [{{"tool": "<tool name>", "arguments": {{...}}}}]}}
Use at most {MAX_ACTIONS} actions. Known tools: {sorted(KNOWN_TOOLS)}"""


class PlanParseError(ValueError):
    pass


def parse_plan(text: str) -> list[ActionRequest]:
    """Extract and validate a JSON action plan from model output."""
    # Strip markdown fences / reasoning text and grab the outer JSON object.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise PlanParseError("Model output did not contain JSON.")

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise PlanParseError(f"Invalid JSON from model: {error}") from error

    raw_actions = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(raw_actions, list):
        raise PlanParseError("JSON must contain an 'actions' list.")
    if len(raw_actions) > MAX_ACTIONS:
        raise PlanParseError(f"Plan exceeds {MAX_ACTIONS} actions.")

    actions = []
    for item in raw_actions:
        if not isinstance(item, dict):
            raise PlanParseError("Each action must be an object.")
        # The model cannot choose its own identity/privileges.
        item = {"tool": item.get("tool", ""), "arguments": item.get("arguments") or {}}
        try:
            actions.append(ActionRequest(**item, actor="ai_agent"))
        except ValidationError as error:
            raise PlanParseError(f"Invalid action: {error}") from error
    return actions


def mock_plan(instruction: str) -> list[ActionRequest]:
    """Keyword-based fallback planner used when no model is configured.

    Targets and recipients are derived from the instruction and the live
    customer table — nothing is hard-coded.
    """
    from app import config
    from app.storage.database import get_customers

    text = instruction.lower()
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", instruction)
    no_email_text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", " ", text)
    numbers = [int(n) for n in re.findall(r"\b\d+\b", no_email_text)]
    live_ids = [c["id"] for c in get_customers()]
    ids = numbers or live_ids[:1] or [1]
    external = any(w in text for w in ("external", "gmail", "personal", "outside", "server"))
    actions: list[dict] = []

    is_update = any(w in text for w in ("update", "change", "deactivate", "set "))

    if "export" in text:
        dest = "external" if external else sorted(config.APPROVED_EXPORT_DESTINATIONS or {"internal_review"})[0]
        actions.append({"tool": "customer.export", "arguments": {"destination": dest}})
    if ("email" in text or "send" in text) and not is_update:
        recipient = emails[0] if emails else (
            "unknown@external.example" if external else f"ops@{config.INTERNAL_EMAIL_DOMAIN}"
        )
        actions.append({"tool": "email.send", "arguments": {
            "to": recipient, "subject": "Customer data", "body": instruction[:200]}})
    if "refund" in text:
        amount = max(numbers) if len(numbers) > 1 else (numbers[0] if numbers and "amount" in text else 50)
        actions.append({"tool": "refund.process", "arguments": {"customer_id": ids[0], "amount": amount}})
    if "delete" in text or "remove" in text:
        targets = live_ids if "all" in text else ids
        actions += [{"tool": "customer.delete", "arguments": {"customer_id": i}} for i in targets]
    if is_update:
        if "email" in text and emails:
            change = {"field": "email", "value": emails[0]}
        else:
            change = {"field": "status", "value": "inactive"}
        actions.append({"tool": "customer.update", "arguments": {"customer_id": ids[0], **change}})
    if not actions and ("list" in text or "all customers" in text):
        actions.append({"tool": "customer.list", "arguments": {}})
    if not actions:
        actions.append({"tool": "customer.read", "arguments": {"customer_id": ids[0]}})

    return [ActionRequest(**a) for a in actions[:MAX_ACTIONS]]


def propose_plan(instruction: str) -> dict:
    """Ask the AI (AMD model or mock) to propose a plan for an instruction."""
    if not llm_client.is_configured():
        return {"source": "mock", "raw_output": None, "actions": mock_plan(instruction)}

    raw = llm_client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]
    )
    return {
        "source": f"amd:{llm_client.get_config()['model']}",
        "raw_output": raw,
        "actions": parse_plan(raw),
    }

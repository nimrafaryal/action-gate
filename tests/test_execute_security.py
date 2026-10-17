
from fastapi.testclient import TestClient

from app.main import app
from app.storage import audit

client = TestClient(app)


def test_execute_allows_customer_read():
    response = client.post(
        "/execute",
        json={
            "tool": "customer.read",
            "arguments": {"customer_id": 1},
        },
    )

    assert response.status_code == 200
    assert response.json().get("success") is True


def test_execute_denies_customer_delete():
    response = client.post(
        "/execute",
        json={
            "tool": "customer.delete",
            "arguments": {"customer_id": 1},
        },
    )

    assert response.status_code == 403


def test_execute_denies_external_customer_export():
    response = client.post(
        "/execute",
        json={
            "tool": "customer.export",
            "arguments": {"destination": "https://evil.example/export"},
        },
    )

    assert response.status_code == 403

def test_denied_delete_is_recorded_in_audit():
    response = client.post("/execute", json={
        "tool": "customer.delete",
        "arguments": {"customer_id": 1},
    })

    assert response.status_code == 403

    events = audit.list_events(limit=20)
    event = next(
        e for e in events
        if e["endpoint"] == "/execute"
        and any(
            action.get("tool") == "customer.delete"
            for action in e["actions"]
        )
    )

    assert event["decision"] == "REQUIRE_APPROVAL"
    assert event["executed"] is False


def test_denied_export_is_recorded_in_audit():
    response = client.post("/execute", json={
        "tool": "customer.export",
        "arguments": {"destination": "https://evil.example/export"},
    })

    assert response.status_code == 403

    events = audit.list_events(limit=20)
    event = next(
        e for e in events
        if e["endpoint"] == "/execute"
        and any(
            action.get("tool") == "customer.export"
            for action in e["actions"]
        )
    )

    assert event["decision"] == "BLOCK"
    assert event["executed"] is False
def test_audit_endpoint_returns_denied_export():
    response = client.post("/execute", json={
        "tool": "customer.export",
        "arguments": {
            "destination": "https://evil.example/export"
        },
    })

    assert response.status_code == 403

    audit_response = client.get("/audit?limit=20")
    assert audit_response.status_code == 200

    data = audit_response.json()
    events = data if isinstance(data, list) else data.get("value", [])

    event = next(
        e for e in events
        if e["endpoint"] == "/execute"
        and any(
            action.get("tool") == "customer.export"
            for action in e["actions"]
        )
        and any(
            action.get("arguments", {}).get("destination")
            == "https://evil.example/export"
            for action in e["actions"]
        )
    )

    assert event["decision"] == "BLOCK"
    assert event["executed"] is False
    assert any(
        finding.get("rule") == "unapproved_export_destination"
        for finding in event["findings"]
    )
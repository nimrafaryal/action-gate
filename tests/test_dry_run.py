
from app.schemas import ActionRequest
from app.storage.database import seed_customers, get_customers
from app.gate.dry_run import simulate_action


def test_delete_dry_run_does_not_change_real_database():
    seed_customers()
    before = get_customers()

    action = ActionRequest(
        tool="customer.delete",
        arguments={"customer_id": 3},
    )

    result = simulate_action(action)

    after = get_customers()

    assert result["dry_run"] is True
    assert result["real_database_modified"] is False
    assert result["record_count_before"] == 5
    assert result["record_count_after"] == 4

    assert len(result["changes"]["deleted"]) == 1
    assert result["changes"]["deleted"][0]["id"] == 3

    assert before == after


def test_update_dry_run_reports_exact_change():
    seed_customers()
    before = get_customers()

    action = ActionRequest(
        tool="customer.update",
        arguments={
            "customer_id": 1,
            "field": "email",
            "value": "new-email@example.com",
        },
    )

    result = simulate_action(action)

    after = get_customers()

    assert result["record_count_before"] == 5
    assert result["record_count_after"] == 5

    assert len(result["changes"]["updated"]) == 1

    change = result["changes"]["updated"][0]
    assert change["before"]["email"] == "ayesha@example.com"
    assert change["after"]["email"] == "new-email@example.com"

    assert before == after


def test_dry_run_rejects_unsupported_tool():
    action = ActionRequest(
        tool="customer.export",
        arguments={},
    )

    try:
        simulate_action(action)
        assert False, "Expected unsupported tool to be rejected"
    except ValueError as error:
        assert "does not support" in str(error)

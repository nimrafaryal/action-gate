
import sqlite3

from app.schemas import ActionRequest
from app.storage.database import DATABASE_PATH


def snapshot_customers(connection):
    """Capture the current customer state."""
    rows = connection.execute(
        """
        SELECT id, name, email, status
        FROM customers
        ORDER BY id
        """
    ).fetchall()

    return [dict(row) for row in rows]


def simulate_action(action: ActionRequest) -> dict:
    """
    Simulate a customer operation inside a rolled-back transaction.
    The real database state must remain unchanged.
    """

    if action.tool not in {"customer.update", "customer.delete"}:
        raise ValueError(
            f"Dry run does not support this tool: {action.tool}"
        )

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Database not found. Run python -m data.seed_demo_data first."
        )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        # Begin a transaction so simulated changes can be rolled back.
        connection.execute("BEGIN")

        before = snapshot_customers(connection)
        args = action.arguments

        if action.tool == "customer.update":
            customer_id = args.get("customer_id")
            field = args.get("field")
            value = args.get("value")

            if not isinstance(customer_id, int) or isinstance(customer_id, bool):
                raise ValueError("customer_id must be an integer.")

            if field not in {"email", "status"}:
                raise ValueError("Only email and status can be updated.")

            if not isinstance(value, str) or not value.strip():
                raise ValueError("Update value must be a non-empty string.")

            cursor = connection.execute(
                f"UPDATE customers SET {field} = ? WHERE id = ?",
                (value, customer_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(f"Customer {customer_id} does not exist.")

        elif action.tool == "customer.delete":
            customer_id = args.get("customer_id")

            if not isinstance(customer_id, int) or isinstance(customer_id, bool):
                raise ValueError("customer_id must be an integer.")

            cursor = connection.execute(
                "DELETE FROM customers WHERE id = ?",
                (customer_id,),
            )

            if cursor.rowcount == 0:
                raise ValueError(f"Customer {customer_id} does not exist.")

        after = snapshot_customers(connection)

        before_by_id = {row["id"]: row for row in before}
        after_by_id = {row["id"]: row for row in after}

        added = [
            after_by_id[key]
            for key in after_by_id.keys() - before_by_id.keys()
        ]

        deleted = [
            before_by_id[key]
            for key in before_by_id.keys() - after_by_id.keys()
        ]

        updated = [
            {
                "before": before_by_id[key],
                "after": after_by_id[key],
            }
            for key in before_by_id.keys() & after_by_id.keys()
            if before_by_id[key] != after_by_id[key]
        ]

        return {
            "tool": action.tool,
            "dry_run": True,
            "real_database_modified": False,
            "changes": {
                "added": added,
                "updated": updated,
                "deleted": deleted,
            },
            "record_count_before": len(before),
            "record_count_after": len(after),
        }

    finally:
        # Undo every simulated database modification.
        connection.rollback()
        connection.close()

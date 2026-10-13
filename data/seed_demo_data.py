
from app.storage.database import seed_customers, get_customers


if __name__ == "__main__":
    seed_customers()

    print("Demo customer database initialized.")
    print(f"Customer records: {len(get_customers())}")

    for customer in get_customers():
        print(customer)

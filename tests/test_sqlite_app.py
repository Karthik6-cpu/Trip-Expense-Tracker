"""Comprehensive tests for the SQLite-backed SplitTrip Pro application."""

import json
import pytest

from app import create_app
from db import Database


@pytest.fixture
def sqlite_app(tmp_path):
    db_file = tmp_path / "test_expenses.db"
    app = create_app(db_path=db_file)
    app.config["TESTING"] = True
    return app.test_client(), db_file


def test_sqlite_initializes_with_default_trip_and_categories(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)

    trips = db.get_trips()
    assert len(trips) == 1
    assert trips[0]["name"] == "Weekend Getaway"
    assert trips[0]["currency_symbol"] == "$"

    categories = db.get_categories()
    assert len(categories) >= 7
    cat_names = [c["name"] for c in categories]
    assert "Food & Dining" in cat_names
    assert "Transport" in cat_names


def test_create_switch_and_update_trips(sqlite_app):
    client, _db_file = sqlite_app

    # Create new trip
    res = client.post("/api/trips", json={
        "name": "Euro Trip 2026",
        "currency_symbol": "€",
        "currency_code": "EUR",
        "organizer_name": "Alex",
        "notes": "Backpacking across Europe",
    })
    assert res.status_code == 201
    trip_data = res.get_json()
    assert trip_data["name"] == "Euro Trip 2026"
    assert trip_data["currency_symbol"] == "€"
    trip_id = trip_data["id"]

    # Update trip
    patch_res = client.patch(f"/api/trips/{trip_id}", json={
        "name": "Euro Trip Summer 2026",
        "currency_symbol": "€",
    })
    assert patch_res.status_code == 200
    assert patch_res.get_json()["name"] == "Euro Trip Summer 2026"

    # List trips
    list_res = client.get("/api/trips")
    trips = list_res.get_json()["trips"]
    assert len(trips) == 2
    assert any(t["id"] == trip_id for t in trips)


def test_friend_crud_and_duplicates_in_sqlite(sqlite_app):
    client, _ = sqlite_app

    # Add friend
    res1 = client.post("/api/friends", json={"name": "Alice", "email": "alice@example.com"})
    assert res1.status_code == 200
    f1 = res1.get_json()
    assert f1["name"] == "Alice"
    assert f1["email"] == "alice@example.com"

    # Duplicate name rejection
    dup = client.post("/api/friends", json={"name": "alice"})
    assert dup.status_code == 400
    assert "already exists" in dup.get_json()["error"]

    # Rename
    renamed = client.patch(f"/api/friends/{f1['id']}", json={"name": "Alice M."})
    assert renamed.status_code == 200
    assert renamed.get_json()["name"] == "Alice M."


def test_custom_split_exact_amounts(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]

    f1 = db.add_friend(trip_id, "Bob")
    f2 = db.add_friend(trip_id, "Charlie")

    # Expense of 100.00: Bob owes 40.00, Charlie owes 35.00, Organizer owes 25.00
    res = client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "Custom Groceries",
        "amount": "100.00",
        "friendIds": [f1["id"], f2["id"]],
        "split_type": "exact",
        "custom_splits": {
            str(f1["id"]): "40.00",
            str(f2["id"]): "35.00",
            "0": "25.00",
        },
    })
    assert res.status_code == 200
    exp = res.get_json()
    assert exp["amount"] == "100.00"
    splits = {s["person_id"]: s["amount"] for s in exp["splits"]}
    assert splits[f1["id"]] == "40.00"
    assert splits[f2["id"]] == "35.00"
    assert splits[0] == "25.00"


def test_custom_split_percentages(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]

    f1 = db.add_friend(trip_id, "Diana")

    # 200.00 total: Diana 40%, Organizer 60%
    res = client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "Hotel Stay",
        "amount": "200.00",
        "friendIds": [f1["id"]],
        "split_type": "percent",
        "custom_splits": {
            str(f1["id"]): 40,
            "0": 60,
        },
    })
    assert res.status_code == 200
    exp = res.get_json()
    splits = {s["person_id"]: s["amount"] for s in exp["splits"]}
    assert splits[f1["id"]] == "80.00"
    assert splits[0] == "120.00"


def test_custom_split_shares(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]

    f1 = db.add_friend(trip_id, "Emma")  # couple = 2 shares
    # Organizer = 1 share. Total shares = 3. Expense = 90.00 -> Emma owes 60.00, Org owes 30.00
    res = client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "AirBnB House",
        "amount": "90.00",
        "friendIds": [f1["id"]],
        "split_type": "shares",
        "custom_splits": {
            str(f1["id"]): 2,
            "0": 1,
        },
    })
    assert res.status_code == 200
    splits = {s["person_id"]: s["amount"] for s in res.get_json()["splits"]}
    assert splits[f1["id"]] == "60.00"
    assert splits[0] == "30.00"


def test_multi_payer_and_debt_simplification(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]

    f1 = db.add_friend(trip_id, "Frank")
    f2 = db.add_friend(trip_id, "Grace")

    # Frank pays 120.00 for Dinner for Frank, Grace, and Organizer (40 each)
    client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "Dinner paid by Frank",
        "amount": "120.00",
        "payer_id": f1["id"],
        "friendIds": [f1["id"], f2["id"]],
        "split_type": "equal",
    })

    settle = client.get(f"/api/settle?trip_id={trip_id}").get_json()
    assert settle["tripTotal"] == "120.00"

    # Frank paid 120, share is 40 -> Frank is owed +80.00
    # Grace paid 0, share is 40 -> Grace owes -40.00
    # Organizer paid 0, share is 40 -> Organizer owes -40.00
    balances = {b["id"]: b["net"] for b in settle["balances"]}
    assert balances[f1["id"]] == "80.00"
    assert balances[f2["id"]] == "-40.00"
    assert balances[0] == "-40.00"

    # Check simplified debts
    simplified = settle["simplifiedDebts"]
    assert len(simplified) == 2
    recipients = {t["to_id"] for t in simplified}
    assert recipients == {f1["id"]}  # All money goes directly to Frank!


def test_settlement_payment_recording(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]

    f1 = db.add_friend(trip_id, "Harry")

    # Organizer pays 100.00 for Harry & Organizer (50.00 each)
    client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "Concert",
        "amount": "100.00",
        "payer_id": 0,
        "friendIds": [f1["id"]],
    })

    # Settle: Harry owes 50.00
    s1 = client.get(f"/api/settle?trip_id={trip_id}").get_json()
    assert len(s1["simplifiedDebts"]) == 1
    assert s1["simplifiedDebts"][0]["amount"] == "50.00"

    # Harry pays back 50.00 via Venmo
    pay_res = client.post("/api/settlements", json={
        "trip_id": trip_id,
        "from_id": f1["id"],
        "to_id": 0,
        "amount": "50.00",
        "date": "2026-11-21",
        "note": "Paid via Venmo",
    })
    assert pay_res.status_code == 201

    # Now debts should be fully settled!
    s2 = client.get(f"/api/settle?trip_id={trip_id}").get_json()
    assert s2["isSettled"] is True
    assert len(s2["simplifiedDebts"]) == 0


def test_csv_export_endpoint(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]
    f1 = db.add_friend(trip_id, "Ivy")

    client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "Museum Tickets",
        "amount": "60.00",
        "friendIds": [f1["id"]],
    })

    export_res = client.get(f"/api/trips/{trip_id}/export/csv")
    assert export_res.status_code == 200
    assert export_res.mimetype == "text/csv"
    text = export_res.get_data(as_text=True)
    assert "Museum Tickets" in text
    assert "60.00" in text


def test_analytics_api_endpoint(sqlite_app):
    client, db_file = sqlite_app
    db = Database(db_file)
    trip_id = db.get_trips()[0]["id"]
    cats = db.get_categories()
    food_cat = next(c for c in cats if "Food" in c["name"])
    f1 = db.add_friend(trip_id, "Jack")

    client.post("/api/expenses", json={
        "trip_id": trip_id,
        "date": "2026-11-20",
        "description": "Pizza Party",
        "amount": "80.00",
        "category_id": food_cat["id"],
        "friendIds": [f1["id"]],
    })

    res = client.get(f"/api/analytics?trip_id={trip_id}")
    assert res.status_code == 200
    analytics = res.get_json()
    assert analytics["total_spent"] == "80.00"
    assert analytics["expense_count"] == 1
    assert len(analytics["categories"]) >= 1
    assert analytics["categories"][0]["name"] == "Food & Dining"

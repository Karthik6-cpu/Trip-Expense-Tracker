import json

import pytest

from app import create_app
from store import Store, empty_trip


@pytest.fixture
def trip(tmp_path):
    path = tmp_path / "trip.json"
    application = create_app(path)
    application.config["TESTING"] = True
    return application.test_client(), path


def test_page_opens_without_sign_in(trip):
    client, _path = trip
    response = client.get("/")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Trip Expense Tracker" in page
    assert "Settle" in page
    assert "Start over" in page
    assert "password" not in page.lower()


def test_missing_file_is_created_empty(trip):
    _client, path = trip
    Store(path).load()

    assert json.loads(path.read_text(encoding="utf-8")) == empty_trip()


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "nested" / "trip.json"
    store = Store(path)
    data = empty_trip()
    data["friends"].append({"id": 1, "name": "Asha"})
    data["nextFriendId"] = 2
    store.save(data)

    assert store.load() == data


def test_add_and_list_friends_in_file_order(trip):
    client, path = trip
    created = client.post("/api/friends", json={"name": " Asha "})
    client.post("/api/friends", json={"name": "Ben"})

    assert created.status_code == 200
    assert created.get_json() == {"id": 1, "name": "Asha"}
    listed = client.get("/api/friends")
    assert listed.get_json() == {
        "friends": [
            {"id": 1, "name": "Asha"},
            {"id": 2, "name": "Ben"},
        ]
    }
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["nextFriendId"] == 3
    assert saved["friends"][0]["name"] == "Asha"


def test_blank_and_duplicate_names_do_not_change_the_file(trip):
    client, path = trip
    client.post("/api/friends", json={"name": "Asha"})
    before = path.read_text(encoding="utf-8")

    blank = client.post("/api/friends", json={"name": "   "})
    duplicate = client.post("/api/friends", json={"name": "asha"})

    assert blank.status_code == 400
    assert duplicate.status_code == 400
    assert "error" in blank.get_json()
    assert path.read_text(encoding="utf-8") == before


def test_record_expense_and_reject_bad_input(trip):
    client, path = trip
    add_friends(client)
    created = client.post(
        "/api/expenses",
        json={
            "date": "2026-11-20",
            "description": " Dinner ",
            "amount": "120.00",
            "friendIds": [1, 2],
        },
    )

    assert created.status_code == 200
    assert created.get_json() == {
        "id": 1,
        "date": "2026-11-20",
        "description": "Dinner",
        "amount": "120.00",
        "friendIds": [1, 2],
        "friendShare": "40.00",
        "organizerShare": "40.00",
    }
    before = path.read_text(encoding="utf-8")
    rejected = [
        {"date": "2026-11-20", "description": "Snack", "amount": "10.00", "friendIds": []},
        {"date": "2026-11-20", "description": "Snack", "amount": "0.00", "friendIds": [1]},
        {"date": "2026-11-20", "description": "   ", "amount": "10.00", "friendIds": [1]},
        {"date": "2026-02-31", "description": "Snack", "amount": "10.00", "friendIds": [1]},
        {"date": "2026-11-20", "description": "Snack", "amount": "10.00", "friendIds": [9]},
        {"date": "2026-11-20", "description": "Snack", "amount": "10.001", "friendIds": [1]},
        {"date": "2026-11-20", "description": "Snack", "amount": "1000000.01", "friendIds": [1]},
    ]
    for body in rejected:
        response = client.post("/api/expenses", json=body)
        assert response.status_code == 400
        assert path.read_text(encoding="utf-8") == before

    listed = client.get("/api/expenses")
    assert listed.get_json()["expenses"][0]["description"] == "Dinner"


def test_expenses_list_by_date_then_id(trip):
    client, _path = trip
    add_friends(client)
    client.post(
        "/api/expenses",
        json={"date": "2026-11-21", "description": "Taxi", "amount": "90.00", "friendIds": [1]},
    )
    client.post(
        "/api/expenses",
        json={"date": "2026-11-20", "description": "Dinner", "amount": "120.00", "friendIds": [1, 2]},
    )

    descriptions = [item["description"] for item in client.get("/api/expenses").get_json()["expenses"]]
    assert descriptions == ["Dinner", "Taxi"]


def test_prd_people_and_settle_totals(trip):
    client, path = trip
    seed_prd(client)
    before = path.read_text(encoding="utf-8")

    settle = client.get("/api/settle")
    people = client.get("/api/people")

    assert settle.get_json() == {
        "tripTotal": "260.00",
        "organizerShare": "87.50",
        "friends": [
            {"id": 1, "name": "Asha", "owes": "62.50"},
            {"id": 2, "name": "Ben", "owes": "62.50"},
            {"id": 3, "name": "Cara", "owes": "47.50"},
        ],
    }
    body = people.get_json()
    assert [friend["total"] for friend in body["friends"]] == ["62.50", "62.50", "47.50"]
    asha = body["friends"][0]
    assert [item["description"] for item in asha["expenses"]] == ["Dinner", "Taxi"]
    assert [item["share"] for item in asha["expenses"]] == ["40.00", "22.50"]
    cara = body["friends"][2]
    assert [item["description"] for item in cara["expenses"]] == ["Snacks", "Taxi"]
    assert path.read_text(encoding="utf-8") == before


def test_rename_does_not_change_what_a_friend_owes(trip):
    client, _path = trip
    seed_prd(client)

    renamed = client.patch("/api/friends/1", json={"name": "Asha R."})
    settle = client.get("/api/settle").get_json()

    assert renamed.status_code == 200
    assert renamed.get_json() == {"id": 1, "name": "Asha R."}
    assert settle["friends"][0] == {"id": 1, "name": "Asha R.", "owes": "62.50"}


def test_removing_a_shared_friend_recalculates(trip):
    client, path = trip
    seed_prd(client)

    removed = client.delete("/api/friends/2")
    settle = client.get("/api/settle").get_json()
    saved = json.loads(path.read_text(encoding="utf-8"))
    dinner = next(item for item in saved["expenses"] if item["description"] == "Dinner")
    taxi = next(item for item in saved["expenses"] if item["description"] == "Taxi")

    assert removed.status_code == 200
    assert removed.get_json() == {"deleted": 2}
    assert dinner["friendIds"] == [1]
    assert taxi["friendIds"] == [1, 3]
    assert settle["friends"] == [
        {"id": 1, "name": "Asha", "owes": "90.00"},
        {"id": 3, "name": "Cara", "owes": "55.00"},
    ]
    assert settle["organizerShare"] == "115.00"
    assert settle["tripTotal"] == "260.00"


def test_cannot_remove_the_only_friend_on_an_expense(trip):
    client, path = trip
    seed_prd(client)
    before = path.read_text(encoding="utf-8")

    response = client.delete("/api/friends/3")

    assert response.status_code == 409
    assert "expense" in response.get_json()["error"]
    assert path.read_text(encoding="utf-8") == before


def test_delete_expense_removes_it_from_settle(trip):
    client, _path = trip
    seed_prd(client)

    deleted = client.delete("/api/expenses/2")
    settle = client.get("/api/settle").get_json()

    assert deleted.status_code == 200
    assert deleted.get_json() == {"deleted": 2}
    owes = {friend["name"]: friend["owes"] for friend in settle["friends"]}
    assert owes == {"Asha": "62.50", "Ben": "62.50", "Cara": "22.50"}
    assert settle["tripTotal"] == "210.00"


def test_update_expense_replaces_who_shared_it(trip):
    client, _path = trip
    seed_prd(client)

    updated = client.patch(
        "/api/expenses/1",
        json={
            "date": "2026-11-19",
            "description": "Group dinner",
            "amount": "90.00",
            "friendIds": [1, 2, 3],
        },
    )
    body = updated.get_json()

    assert updated.status_code == 200
    assert body["description"] == "Group dinner"
    assert body["friendShare"] == "22.50"
    assert body["organizerShare"] == "22.50"
    assert body["friendIds"] == [1, 2, 3]


def test_unknown_ids_return_404(trip):
    client, path = trip
    add_friends(client)
    before = path.read_text(encoding="utf-8")

    assert client.patch("/api/friends/9", json={"name": "No"}).status_code == 404
    assert client.delete("/api/friends/9").status_code == 404
    assert client.delete("/api/expenses/9").status_code == 404
    assert path.read_text(encoding="utf-8") == before


def test_deleted_friend_id_is_not_reused(trip):
    client, _path = trip
    client.post("/api/friends", json={"name": "Asha"})
    client.post("/api/friends", json={"name": "Ben"})
    client.delete("/api/friends/1")

    created = client.post("/api/friends", json={"name": "Cara"})

    assert created.get_json()["id"] == 3
    assert client.get("/api/friends").get_json() == {
        "friends": [
            {"id": 2, "name": "Ben"},
            {"id": 3, "name": "Cara"},
        ]
    }


def test_start_over_writes_the_empty_trip(trip):
    client, path = trip
    seed_prd(client)

    cleared = client.delete("/api/trip")
    created = client.post("/api/friends", json={"name": "Asha"})

    assert cleared.status_code == 200
    assert cleared.get_json() == {"friends": [], "expenses": []}
    assert created.get_json() == {"id": 1, "name": "Asha"}
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["friends"] == [{"id": 1, "name": "Asha"}]
    assert saved["expenses"] == []


def test_unreadable_trip_file_returns_500(trip):
    client, path = trip
    path.write_text("{", encoding="utf-8")

    response = client.get("/api/friends")

    assert response.status_code == 500
    assert "error" in response.get_json()


def test_unknown_route_returns_404(trip):
    client, _path = trip
    response = client.get("/api/missing")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found."}


def add_friends(client):
    for name in ("Asha", "Ben", "Cara"):
        response = client.post("/api/friends", json={"name": name})
        assert response.status_code == 200


def seed_prd(client):
    add_friends(client)
    expenses = [
        ("2026-11-20", "Dinner", "120.00", [1, 2]),
        ("2026-11-20", "Snacks", "50.00", [3]),
        ("2026-11-21", "Taxi", "90.00", [1, 2, 3]),
    ]
    for date, description, amount, friend_ids in expenses:
        response = client.post(
            "/api/expenses",
            json={
                "date": date,
                "description": description,
                "amount": amount,
                "friendIds": friend_ids,
            },
        )
        assert response.status_code == 200

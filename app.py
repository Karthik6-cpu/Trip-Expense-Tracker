"""Trip Expense Tracker & Splitter.

Supports both SQLite database (default for multi-trip, categories, custom splits, settlements)
and JSON file store (for legacy compatibility).
"""

from datetime import datetime
import json
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)

from db import Database
from split import format_cents, friend_and_organizer_shares, parse_amount_to_cents
from store import Store, StoreError, empty_trip

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "expenses.db"
DEFAULT_JSON = ROOT / "data" / "trip.json"
MAX_CENTS = 100_000_000


class ValidationError(Exception):
    """The request cannot be processed due to invalid input."""


def create_app(trip_path=None, db_path=None):
    app = Flask(__name__)

    # Detect legacy JSON test mode: if trip_path is explicitly a .json file
    is_json_mode = False
    if trip_path:
        p = Path(trip_path)
        if p.suffix == ".json":
            is_json_mode = True
            app.config["JSON_PATH"] = p

    app.config["LEGACY_JSON_MODE"] = is_json_mode
    if not is_json_mode:
        database_path = Path(db_path) if db_path else DEFAULT_DB
        app.config["DB_PATH"] = database_path
        app.config["DATABASE"] = Database(database_path)
    else:
        app.config["STORE"] = Store(app.config["JSON_PATH"])

    # ---------------------------------------------------------
    # Web UI
    # ---------------------------------------------------------
    @app.get("/")
    def index():
        return render_template("index.html")

    # ---------------------------------------------------------
    # Helper to get active database or trip_id
    # ---------------------------------------------------------
    def get_db():
        return current_app.config["DATABASE"]

    def get_active_trip_id():
        # Query param or header or default to first trip
        trip_id = request.args.get("trip_id")
        if trip_id:
            try:
                return int(trip_id)
            except ValueError:
                pass
        trips = get_db().get_trips()
        if trips:
            return trips[0]["id"]
        # Create default if none
        new_trip = get_db().create_trip("My Trip")
        return new_trip["id"]

    # ---------------------------------------------------------
    # Trips API (SQLite Mode)
    # ---------------------------------------------------------
    @app.get("/api/trips")
    def list_trips():
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"trips": [{"id": 1, "name": "Current Trip", "currency_symbol": "$", "total_spent": "0.00"}]})
        db = get_db()
        return jsonify({"trips": db.get_trips()})

    @app.post("/api/trips")
    def create_trip():
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"id": 1, "name": "Trip"})
        data = request_json()
        name = data.get("name", "").strip()
        currency_symbol = data.get("currency_symbol", "$").strip() or "$"
        currency_code = data.get("currency_code", "USD").strip() or "USD"
        organizer_name = data.get("organizer_name", "You (Organizer)").strip() or "You (Organizer)"
        notes = data.get("notes", "").strip()

        try:
            trip = get_db().create_trip(name, currency_symbol, currency_code, organizer_name, notes)
            return jsonify(trip), 201
        except ValueError as e:
            return fail(str(e), 400)

    @app.get("/api/trips/<int:trip_id>")
    def get_trip_details(trip_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"id": 1, "name": "Current Trip", "currency_symbol": "$"})
        trip = get_db().get_trip(trip_id)
        if not trip:
            return fail("Trip not found.", 404)
        return jsonify(trip)

    @app.patch("/api/trips/<int:trip_id>")
    def update_trip(trip_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"id": trip_id})
        data = request_json()
        try:
            updated = get_db().update_trip(
                trip_id,
                name=data.get("name"),
                currency_symbol=data.get("currency_symbol"),
                currency_code=data.get("currency_code"),
                organizer_name=data.get("organizer_name"),
                notes=data.get("notes"),
            )
            return jsonify(updated)
        except KeyError:
            return fail("Trip not found.", 404)
        except ValueError as e:
            return fail(str(e), 400)

    @app.delete("/api/trips/<int:trip_id>")
    def delete_trip(trip_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"deleted": trip_id})
        try:
            get_db().delete_trip(trip_id)
            return jsonify({"deleted": trip_id})
        except KeyError:
            return fail("Trip not found.", 404)

    @app.post("/api/trips/<int:trip_id>/clear")
    def clear_trip_contents(trip_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"cleared": trip_id})
        try:
            get_db().clear_trip(trip_id)
            return jsonify({"cleared": trip_id})
        except KeyError:
            return fail("Trip not found.", 404)

    @app.get("/api/trips/<int:trip_id>/export/csv")
    def export_csv(trip_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return Response("ID,Description,Amount\n", mimetype="text/csv")
        try:
            csv_content = get_db().export_csv(trip_id)
            trip = get_db().get_trip(trip_id)
            filename = f"{trip['name'].replace(' ', '_')}_expenses.csv"
            return Response(
                csv_content,
                mimetype="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except KeyError:
            return fail("Trip not found.", 404)

    @app.get("/api/trips/<int:trip_id>/export/json")
    def export_json(trip_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({})
        try:
            data = get_db().export_json(trip_id)
            return jsonify(data)
        except KeyError:
            return fail("Trip not found.", 404)

    # ---------------------------------------------------------
    # Categories API
    # ---------------------------------------------------------
    @app.get("/api/categories")
    def list_categories():
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"categories": []})
        return jsonify({"categories": get_db().get_categories()})

    # ---------------------------------------------------------
    # Friends API
    # ---------------------------------------------------------
    @app.get("/api/friends")
    def list_friends():
        if current_app.config.get("LEGACY_JSON_MODE"):
            data = load_trip_json()
            return jsonify({"friends": public_friends_json(data)})

        trip_id = get_active_trip_id()
        friends = get_db().get_friends(trip_id)
        return jsonify({"friends": friends})

    @app.post("/api/friends")
    def add_friend():
        data = request_json()

        if current_app.config.get("LEGACY_JSON_MODE"):
            trip_data = load_trip_json()
            name = parse_name_json(data, trip_data["friends"])
            friend = {"id": trip_data["nextFriendId"], "name": name}
            trip_data["friends"].append(friend)
            trip_data["nextFriendId"] += 1
            save_trip_json(trip_data)
            return jsonify(friend)

        trip_id = data.get("trip_id") or get_active_trip_id()
        name = data.get("name", "")
        email = data.get("email", "")
        phone = data.get("phone", "")
        color = data.get("color")

        try:
            created = get_db().add_friend(trip_id, name, email, phone, color)
            return jsonify(created)
        except ValueError as e:
            return fail(str(e), 400)
        except KeyError:
            return fail("Trip not found.", 404)

    @app.patch("/api/friends/<int:friend_id>")
    def rename_friend(friend_id):
        data = request_json()

        if current_app.config.get("LEGACY_JSON_MODE"):
            trip_data = load_trip_json()
            friend = find_friend_json(trip_data, friend_id)
            friend["name"] = parse_name_json(data, trip_data["friends"], ignore_id=friend_id)
            save_trip_json(trip_data)
            return jsonify({"id": friend["id"], "name": friend["name"]})

        name = data.get("name", "")
        try:
            updated = get_db().rename_friend(friend_id, name)
            return jsonify(updated)
        except KeyError:
            return fail("Friend not found.", 404)
        except ValueError as e:
            return fail(str(e), 400)

    @app.delete("/api/friends/<int:friend_id>")
    def remove_friend(friend_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            trip_data = load_trip_json()
            friend = find_friend_json(trip_data, friend_id)
            blocking = [
                expense
                for expense in trip_data["expenses"]
                if friend["id"] in expense["friendIds"] and len(expense["friendIds"]) == 1
            ]
            if blocking:
                return fail(
                    "This friend is the only person on an expense. Change or delete that expense first.",
                    409,
                )
            trip_data["friends"] = [item for item in trip_data["friends"] if item["id"] != friend["id"]]
            for expense in trip_data["expenses"]:
                expense["friendIds"] = [
                    item for item in expense["friendIds"] if item != friend["id"]
                ]
            save_trip_json(trip_data)
            return jsonify({"deleted": friend["id"]})

        try:
            deleted_id = get_db().delete_friend(friend_id)
            return jsonify({"deleted": deleted_id})
        except KeyError:
            return fail("Friend not found.", 404)
        except ValueError as e:
            return fail(str(e), 409)

    # ---------------------------------------------------------
    # Expenses API
    # ---------------------------------------------------------
    @app.get("/api/expenses")
    def list_expenses():
        if current_app.config.get("LEGACY_JSON_MODE"):
            data = load_trip_json()
            expenses = sorted(data["expenses"], key=lambda item: (item["date"], item["id"]))
            return jsonify({"expenses": [public_expense_json(item) for item in expenses]})

        trip_id = get_active_trip_id()
        cat_id = request.args.get("category_id")
        f_id = request.args.get("friend_id")
        search = request.args.get("search")

        expenses = get_db().get_expenses(trip_id, category_id=cat_id, friend_id=f_id, search=search)
        return jsonify({"expenses": expenses})

    @app.post("/api/expenses")
    def add_expense():
        data = request_json()

        if current_app.config.get("LEGACY_JSON_MODE"):
            trip_data = load_trip_json()
            expense = parse_expense_json(data, trip_data["friends"])
            expense["id"] = trip_data["nextExpenseId"]
            trip_data["expenses"].append(expense)
            trip_data["nextExpenseId"] += 1
            save_trip_json(trip_data)
            return jsonify(public_expense_json(expense))

        trip_id = data.get("trip_id") or get_active_trip_id()
        date = data.get("date", "")
        description = data.get("description", "")
        amount = data.get("amount", "")
        friend_ids = data.get("friendIds", [])
        payer_id = int(data.get("payer_id", 0))
        category_id = data.get("category_id")
        split_type = data.get("split_type", "equal")
        custom_splits = data.get("custom_splits")
        notes = data.get("notes", "")
        include_organizer = data.get("include_organizer", True)

        try:
            created = get_db().add_expense(
                trip_id=trip_id,
                date=date,
                description=description,
                amount=amount,
                friend_ids=friend_ids,
                payer_id=payer_id,
                category_id=category_id,
                split_type=split_type,
                custom_splits=custom_splits,
                notes=notes,
                include_organizer=include_organizer,
            )
            return jsonify(created)
        except (ValueError, KeyError) as e:
            return fail(str(e), 400)

    @app.get("/api/expenses/<int:expense_id>")
    def get_expense(expense_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            data = load_trip_json()
            exp = find_expense_json(data, expense_id)
            return jsonify(public_expense_json(exp))

        exp = get_db().get_expense(expense_id)
        if not exp:
            return fail("Expense not found.", 404)
        return jsonify(exp)

    @app.patch("/api/expenses/<int:expense_id>")
    def update_expense(expense_id):
        data = request_json()

        if current_app.config.get("LEGACY_JSON_MODE"):
            trip_data = load_trip_json()
            current = find_expense_json(trip_data, expense_id)
            incoming = parse_expense_json(data, trip_data["friends"])
            current["date"] = incoming["date"]
            current["description"] = incoming["description"]
            current["amountCents"] = incoming["amountCents"]
            current["friendIds"] = incoming["friendIds"]
            save_trip_json(trip_data)
            return jsonify(public_expense_json(current))

        date = data.get("date", "")
        description = data.get("description", "")
        amount = data.get("amount", "")
        friend_ids = data.get("friendIds", [])
        payer_id = int(data.get("payer_id", 0))
        category_id = data.get("category_id")
        split_type = data.get("split_type", "equal")
        custom_splits = data.get("custom_splits")
        notes = data.get("notes", "")
        include_organizer = data.get("include_organizer", True)

        try:
            updated = get_db().update_expense(
                expense_id=expense_id,
                date=date,
                description=description,
                amount=amount,
                friend_ids=friend_ids,
                payer_id=payer_id,
                category_id=category_id,
                split_type=split_type,
                custom_splits=custom_splits,
                notes=notes,
                include_organizer=include_organizer,
            )
            return jsonify(updated)
        except KeyError:
            return fail("Expense not found.", 404)
        except ValueError as e:
            return fail(str(e), 400)

    @app.delete("/api/expenses/<int:expense_id>")
    def remove_expense(expense_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            trip_data = load_trip_json()
            find_expense_json(trip_data, expense_id)
            trip_data["expenses"] = [item for item in trip_data["expenses"] if item["id"] != expense_id]
            save_trip_json(trip_data)
            return jsonify({"deleted": expense_id})

        try:
            deleted_id = get_db().delete_expense(expense_id)
            return jsonify({"deleted": deleted_id})
        except KeyError:
            return fail("Expense not found.", 404)

    # ---------------------------------------------------------
    # People & Settle & Settlements API
    # ---------------------------------------------------------
    @app.get("/api/people")
    def people():
        if current_app.config.get("LEGACY_JSON_MODE"):
            data = load_trip_json()
            return jsonify({"friends": people_view_json(data)})

        trip_id = get_active_trip_id()
        rows = get_db().get_people_summary(trip_id)
        return jsonify({"friends": rows})

    @app.get("/api/settle")
    def settle():
        if current_app.config.get("LEGACY_JSON_MODE"):
            data = load_trip_json()
            return jsonify(settle_view_json(data))

        trip_id = get_active_trip_id()
        summary = get_db().get_settle_summary(trip_id)
        return jsonify(summary)

    @app.post("/api/settlements")
    def record_settlement():
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"id": 1})

        data = request_json()
        trip_id = data.get("trip_id") or get_active_trip_id()
        from_id = data.get("from_id")
        to_id = data.get("to_id")
        amount = data.get("amount")
        date = data.get("date", datetime.today().strftime("%Y-%m-%d"))
        note = data.get("note", "")

        try:
            created = get_db().add_settlement(trip_id, from_id, to_id, amount, date, note)
            return jsonify(created), 201
        except ValueError as e:
            return fail(str(e), 400)

    @app.get("/api/settlements")
    def list_settlements():
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"settlements": []})

        trip_id = get_active_trip_id()
        items = get_db().get_settlements(trip_id)
        return jsonify({"settlements": items})

    @app.delete("/api/settlements/<int:settlement_id>")
    def delete_settlement(settlement_id):
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"deleted": settlement_id})

        try:
            deleted_id = get_db().delete_settlement(settlement_id)
            return jsonify({"deleted": deleted_id})
        except KeyError:
            return fail("Settlement not found.", 404)

    @app.delete("/api/trip")
    def start_over():
        if current_app.config.get("LEGACY_JSON_MODE"):
            data = empty_trip()
            save_trip_json(data)
            return jsonify({"friends": [], "expenses": []})

        trip_id = get_active_trip_id()
        get_db().clear_trip(trip_id)
        return jsonify({"friends": [], "expenses": []})

    # ---------------------------------------------------------
    # Analytics API
    # ---------------------------------------------------------
    @app.get("/api/analytics")
    def analytics():
        if current_app.config.get("LEGACY_JSON_MODE"):
            return jsonify({"total_spent": "0.00", "categories": [], "timeline": []})

        trip_id = get_active_trip_id()
        stats = get_db().get_analytics(trip_id)
        return jsonify(stats)

    # ---------------------------------------------------------
    # Error Handlers
    # ---------------------------------------------------------
    @app.errorhandler(StoreError)
    def store_failed(error):
        return fail(str(error), 500)

    @app.errorhandler(404)
    def missing(error):
        description = getattr(error, "description", "")
        if description in {"Friend not found.", "Expense not found.", "Trip not found."}:
            return fail(description, 404)
        return fail("Not found.", 404)

    @app.errorhandler(ValidationError)
    def invalid(error):
        return fail(str(error), 400)

    return app


# =============================================================
# JSON Mode Helper Functions (Preserving 100% legacy compatibility)
# =============================================================
def load_trip_json():
    return current_app.config["STORE"].load()


def save_trip_json(data):
    current_app.config["STORE"].save(data)


def fail(message, status):
    return jsonify({"error": message}), status


def request_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send the request as JSON.")
    return data


def parse_name_json(data, friends, ignore_id=None):
    raw = data.get("name")
    if not isinstance(raw, str):
        raise ValidationError("Friend name cannot be blank.")
    name = raw.strip()
    if not name:
        raise ValidationError("Friend name cannot be blank.")
    if len(name) > 40:
        raise ValidationError("Friend name cannot be longer than 40 characters.")
    for friend in friends:
        if friend["id"] == ignore_id:
            continue
        if friend["name"].strip().casefold() == name.casefold():
            raise ValidationError("A friend with this name is already on the trip.")
    return name


def parse_expense_json(data, friends):
    date = parse_date_json(data.get("date"))
    description = parse_description_json(data.get("description"))
    amount_cents = parse_amount_json(data.get("amount"))
    friend_ids = parse_friend_ids_json(data.get("friendIds"), friends)
    return {
        "date": date,
        "description": description,
        "amountCents": amount_cents,
        "friendIds": friend_ids,
    }


def parse_date_json(raw):
    if not isinstance(raw, str):
        raise ValidationError("Choose a date for the expense.")
    value = raw.strip()
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("Enter a valid calendar date in YYYY-MM-DD format.") from exc
    return parsed.strftime("%Y-%m-%d")


def parse_description_json(raw):
    if not isinstance(raw, str):
        raise ValidationError("Enter a description.")
    description = raw.strip()
    if not description:
        raise ValidationError("Enter a description.")
    if len(description) > 80:
        raise ValidationError("Description cannot be longer than 80 characters.")
    return description


def parse_amount_json(raw):
    if not isinstance(raw, str):
        raise ValidationError("Enter an amount from 0.01 to 1000000.00 with two decimal places.")
    text = raw.strip()
    parts = text.split(".")
    if len(parts) != 2 or len(parts[1]) != 2:
        raise ValidationError("Enter an amount from 0.01 to 1000000.00 with two decimal places.")
    if not (parts[0].isdigit() and parts[1].isdigit()):
        raise ValidationError("Enter an amount from 0.01 to 1000000.00 with two decimal places.")
    cents = int(parts[0]) * 100 + int(parts[1])
    if cents <= 0 or cents > MAX_CENTS:
        raise ValidationError("Enter an amount from 0.01 to 1000000.00 with two decimal places.")
    return cents


def parse_friend_ids_json(raw, friends):
    if not isinstance(raw, list) or len(raw) == 0:
        raise ValidationError("Select at least one friend.")
    known = {friend["id"] for friend in friends}
    clean = []
    for item in raw:
        if not isinstance(item, int) or item not in known:
            raise ValidationError("Select friends who are on the trip.")
        if item not in clean:
            clean.append(item)
    if not clean:
        raise ValidationError("Select at least one friend.")
    return clean


def public_friends_json(data):
    return [{"id": friend["id"], "name": friend["name"]} for friend in data["friends"]]


def public_expense_json(expense):
    friend_share, organizer_share = friend_and_organizer_shares(
        expense["amountCents"], len(expense["friendIds"])
    )
    return {
        "id": expense["id"],
        "date": expense["date"],
        "description": expense["description"],
        "amount": format_cents(expense["amountCents"]),
        "friendIds": list(expense["friendIds"]),
        "friendShare": format_cents(friend_share),
        "organizerShare": format_cents(organizer_share),
    }


def people_view_json(data):
    ordered = sorted(data["expenses"], key=lambda item: (item["date"], item["id"]))
    rows = []
    for friend in data["friends"]:
        items = []
        total = 0
        for expense in ordered:
            if friend["id"] not in expense["friendIds"]:
                continue
            friend_share, _organizer_share = friend_and_organizer_shares(
                expense["amountCents"], len(expense["friendIds"])
            )
            total += friend_share
            items.append(
                {
                    "expenseId": expense["id"],
                    "date": expense["date"],
                    "description": expense["description"],
                    "share": format_cents(friend_share),
                }
            )
        rows.append(
            {
                "id": friend["id"],
                "name": friend["name"],
                "total": format_cents(total),
                "expenses": items,
            }
        )
    return rows


def settle_view_json(data):
    owes = {friend["id"]: 0 for friend in data["friends"]}
    organizer_total = 0
    trip_total = 0
    for expense in data["expenses"]:
        friend_share, organizer_share = friend_and_organizer_shares(
            expense["amountCents"], len(expense["friendIds"])
        )
        trip_total += expense["amountCents"]
        organizer_total += organizer_share
        for friend_id in expense["friendIds"]:
            owes[friend_id] += friend_share
    return {
        "tripTotal": format_cents(trip_total),
        "organizerShare": format_cents(organizer_total),
        "friends": [
            {"id": friend["id"], "name": friend["name"], "owes": format_cents(owes[friend["id"]])}
            for friend in data["friends"]
        ],
    }


def find_friend_json(data, friend_id):
    for friend in data["friends"]:
        if friend["id"] == friend_id:
            return friend
    abort(404, description="Friend not found.")


def find_expense_json(data, expense_id):
    for expense in data["expenses"]:
        if expense["id"] == expense_id:
            return expense
    abort(404, description="Expense not found.")


if __name__ == "__main__":
    app = create_app()
    print("✨ SplitTrip Pro running on http://127.0.0.1:5000 (SQLite Database)")
    app.run(debug=True, host="127.0.0.1", port=5000)

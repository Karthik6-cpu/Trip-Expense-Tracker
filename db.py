"""SQLite database management for Trip Expense Tracker with multi-trip support."""

import csv
import io
import json
from pathlib import Path
import sqlite3

from split import calculate_splits, format_cents, parse_amount_to_cents, simplify_debts

DEFAULT_CATEGORIES = [
    ("Food & Dining", "🍕", "#F59E0B"),
    ("Transport", "🚗", "#3B82F6"),
    ("Lodging", "🏨", "#8B5CF6"),
    ("Activities", "🎟️", "#EC4899"),
    ("Groceries", "🛒", "#10B981"),
    ("Shopping", "🛍️", "#F97316"),
    ("Other", "💡", "#6B7280"),
]

AVATAR_COLORS = [
    "#4F46E5", "#06B6D4", "#10B981", "#F59E0B",
    "#EF4444", "#EC4899", "#8B5CF6", "#14B8A6",
]


class Database:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._mem_conn = None
        else:
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys = ON")
        self.init_db()

    def get_connection(self):
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    currency_symbol TEXT NOT NULL DEFAULT '$',
                    currency_code TEXT NOT NULL DEFAULT 'USD',
                    organizer_name TEXT NOT NULL DEFAULT 'You (Organizer)',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_archived INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    icon TEXT NOT NULL,
                    color TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS friends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    color TEXT DEFAULT '#4F46E5',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trip_id, name COLLATE NOCASE)
                );

                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                    payer_id INTEGER NOT NULL DEFAULT 0,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    split_type TEXT NOT NULL DEFAULT 'equal',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS expense_splits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
                    person_id INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    share_value REAL DEFAULT 0,
                    UNIQUE(expense_id, person_id)
                );

                CREATE TABLE IF NOT EXISTS settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                    from_id INTEGER NOT NULL,
                    to_id INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Seed default categories if empty
            count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO categories (name, icon, color) VALUES (?, ?, ?)",
                    DEFAULT_CATEGORIES,
                )

            # Ensure at least one active trip exists
            trip_count = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
            if trip_count == 0:
                conn.execute(
                    "INSERT INTO trips (name, currency_symbol, currency_code, organizer_name) VALUES (?, ?, ?, ?)",
                    ("Weekend Getaway", "$", "USD", "You (Organizer)"),
                )

    # -------------------------------------------------------------
    # TRIPS
    # -------------------------------------------------------------
    def get_trips(self):
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT t.*, 
                       (SELECT COUNT(*) FROM friends f WHERE f.trip_id = t.id) as friend_count,
                       (SELECT COUNT(*) FROM expenses e WHERE e.trip_id = t.id) as expense_count,
                       (SELECT COALESCE(SUM(amount_cents), 0) FROM expenses e WHERE e.trip_id = t.id) as total_spent_cents
                FROM trips t
                ORDER BY t.id DESC
            """).fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "currency_symbol": row["currency_symbol"],
                    "currency_code": row["currency_code"],
                    "organizer_name": row["organizer_name"],
                    "notes": row["notes"],
                    "created_at": row["created_at"],
                    "is_archived": bool(row["is_archived"]),
                    "friend_count": row["friend_count"],
                    "expense_count": row["expense_count"],
                    "total_spent": format_cents(row["total_spent_cents"]),
                    "total_spent_cents": row["total_spent_cents"],
                }
                for row in rows
            ]

    def get_trip(self, trip_id):
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def create_trip(self, name, currency_symbol="$", currency_code="USD", organizer_name="You (Organizer)", notes=""):
        name = name.strip()
        if not name:
            raise ValueError("Trip name cannot be empty.")
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO trips (name, currency_symbol, currency_code, organizer_name, notes) VALUES (?, ?, ?, ?, ?)",
                (name, currency_symbol.strip() or "$", currency_code.strip() or "USD", organizer_name.strip() or "You (Organizer)", notes.strip()),
            )
            trip_id = cursor.lastrowid
            conn.commit()
        return self.get_trip(trip_id)

    def update_trip(self, trip_id, name=None, currency_symbol=None, currency_code=None, organizer_name=None, notes=None):
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")
        new_name = name.strip() if name is not None else trip["name"]
        new_sym = currency_symbol.strip() if currency_symbol is not None else trip["currency_symbol"]
        new_code = currency_code.strip() if currency_code is not None else trip["currency_code"]
        new_org = organizer_name.strip() if organizer_name is not None else trip["organizer_name"]
        new_notes = notes.strip() if notes is not None else trip["notes"]

        if not new_name:
            raise ValueError("Trip name cannot be empty.")

        with self.get_connection() as conn:
            conn.execute(
                "UPDATE trips SET name = ?, currency_symbol = ?, currency_code = ?, organizer_name = ?, notes = ? WHERE id = ?",
                (new_name, new_sym, new_code, new_org, new_notes, trip_id),
            )
            conn.commit()
        return self.get_trip(trip_id)

    def delete_trip(self, trip_id):
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")
        with self.get_connection() as conn:
            conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
            # Ensure at least one trip remains
            rem = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
            if rem == 0:
                conn.execute(
                    "INSERT INTO trips (name, currency_symbol, currency_code, organizer_name) VALUES (?, ?, ?, ?)",
                    ("New Trip", "$", "USD", "You (Organizer)"),
                )
            conn.commit()
            return True

    def clear_trip(self, trip_id):
        """Reset friends, expenses, settlements for a trip while preserving trip details."""
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")
        with self.get_connection() as conn:
            conn.execute("DELETE FROM expenses WHERE trip_id = ?", (trip_id,))
            conn.execute("DELETE FROM friends WHERE trip_id = ?", (trip_id,))
            conn.execute("DELETE FROM settlements WHERE trip_id = ?", (trip_id,))
            conn.commit()
        return True

    # -------------------------------------------------------------
    # CATEGORIES
    # -------------------------------------------------------------
    def get_categories(self):
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM categories ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------
    # FRIENDS
    # -------------------------------------------------------------
    def get_friends(self, trip_id):
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM friends WHERE trip_id = ? ORDER BY id ASC",
                (trip_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_friend(self, trip_id, name, email="", phone="", color=None):
        name = name.strip()
        if not name:
            raise ValueError("Friend name cannot be blank.")
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")

        with self.get_connection() as conn:
            # Check duplicate name case-insensitively
            existing = conn.execute(
                "SELECT id FROM friends WHERE trip_id = ? AND name = ? COLLATE NOCASE",
                (trip_id, name),
            ).fetchone()
            if existing:
                raise ValueError("A friend with this name already exists in this trip.")

            if not color:
                idx = conn.execute("SELECT COUNT(*) FROM friends WHERE trip_id = ?", (trip_id,)).fetchone()[0]
                color = AVATAR_COLORS[idx % len(AVATAR_COLORS)]

            cursor = conn.execute(
                "INSERT INTO friends (trip_id, name, email, phone, color) VALUES (?, ?, ?, ?, ?)",
                (trip_id, name, email.strip(), phone.strip(), color),
            )
            friend_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM friends WHERE id = ?", (friend_id,)).fetchone()
            res = dict(row)
            conn.commit()
            return res

    def rename_friend(self, friend_id, name):
        name = name.strip()
        if not name:
            raise ValueError("Friend name cannot be blank.")
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM friends WHERE id = ?", (friend_id,)).fetchone()
            if not row:
                raise KeyError("Friend not found.")
            trip_id = row["trip_id"]

            existing = conn.execute(
                "SELECT id FROM friends WHERE trip_id = ? AND name = ? COLLATE NOCASE AND id != ?",
                (trip_id, name, friend_id),
            ).fetchone()
            if existing:
                raise ValueError("A friend with this name already exists.")

            conn.execute("UPDATE friends SET name = ? WHERE id = ?", (name, friend_id))
            conn.commit()
            return {"id": friend_id, "name": name}

    def delete_friend(self, friend_id):
        with self.get_connection() as conn:
            friend = conn.execute("SELECT * FROM friends WHERE id = ?", (friend_id,)).fetchone()
            if not friend:
                raise KeyError("Friend not found.")

            # Check if this friend is the only participant in any expense
            blocking = conn.execute("""
                SELECT es.expense_id 
                FROM expense_splits es
                WHERE es.person_id = ? 
                  AND (SELECT COUNT(*) FROM expense_splits es2 WHERE es2.expense_id = es.expense_id) = 1
            """, (friend_id,)).fetchone()

            if blocking:
                raise ValueError("This friend is the only person on an expense. Change or delete that expense first.")

            # Also check if expense has this friend as the only friend participant
            legacy_blocking = conn.execute("""
                SELECT es.expense_id
                FROM expense_splits es
                WHERE es.person_id = ?
                  AND (SELECT COUNT(*) FROM expense_splits es2 WHERE es2.expense_id = es.expense_id AND es2.person_id != 0) = 1
            """, (friend_id,)).fetchone()

            if legacy_blocking:
                raise ValueError("This friend is the only person on an expense. Change or delete that expense first.")

            # Recalculate remaining splits for affected expenses
            affected_expenses = conn.execute(
                "SELECT DISTINCT expense_id FROM expense_splits WHERE person_id = ?",
                (friend_id,),
            ).fetchall()

            conn.execute("DELETE FROM expense_splits WHERE person_id = ?", (friend_id,))
            conn.execute("DELETE FROM settlements WHERE from_id = ? OR to_id = ?", (friend_id, friend_id))
            conn.execute("DELETE FROM friends WHERE id = ?", (friend_id,))

            # Re-split remaining participants equally if split_type was equal
            for row in affected_expenses:
                exp_id = row["expense_id"]
                exp = conn.execute("SELECT * FROM expenses WHERE id = ?", (exp_id,)).fetchone()
                if exp and exp["split_type"] == "equal":
                    remaining_splits = conn.execute(
                        "SELECT person_id FROM expense_splits WHERE expense_id = ?", (exp_id,)
                    ).fetchall()
                    if remaining_splits:
                        parts = [r["person_id"] for r in remaining_splits]
                        new_splits = calculate_splits(exp["amount_cents"], exp["payer_id"], parts, "equal")
                        for pid, share in new_splits.items():
                            conn.execute(
                                "UPDATE expense_splits SET amount_cents = ? WHERE expense_id = ? AND person_id = ?",
                                (share, exp_id, pid),
                            )

            conn.commit()
            return friend_id

    # -------------------------------------------------------------
    # EXPENSES
    # -------------------------------------------------------------
    def get_expenses(self, trip_id, category_id=None, friend_id=None, search=None):
        with self.get_connection() as conn:
            query = """
                SELECT e.*, c.name as category_name, c.icon as category_icon, c.color as category_color,
                       CASE WHEN e.payer_id = 0 THEN (SELECT organizer_name FROM trips WHERE id = e.trip_id)
                            ELSE (SELECT name FROM friends WHERE id = e.payer_id)
                       END as payer_name
                FROM expenses e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE e.trip_id = ?
            """
            params = [trip_id]

            if category_id:
                query += " AND e.category_id = ?"
                params.append(category_id)
            if search:
                query += " AND (e.description LIKE ? OR e.notes LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY e.date ASC, e.id ASC"
            rows = conn.execute(query, params).fetchall()

            result = []
            for row in rows:
                splits = conn.execute(
                    "SELECT person_id, amount_cents, share_value FROM expense_splits WHERE expense_id = ?",
                    (row["id"],),
                ).fetchall()

                person_ids = [s["person_id"] for s in splits]
                friend_ids = [s["person_id"] for s in splits if s["person_id"] != 0]

                # Filter by friend_id if requested
                if friend_id is not None:
                    if int(friend_id) not in person_ids:
                        continue

                # PRD compatibility shares
                f_share_cents = 0
                org_share_cents = 0
                for s in splits:
                    if s["person_id"] == 0:
                        org_share_cents = s["amount_cents"]
                    else:
                        f_share_cents = s["amount_cents"]

                item = {
                    "id": row["id"],
                    "trip_id": row["trip_id"],
                    "payer_id": row["payer_id"],
                    "payer_name": row["payer_name"] or "You (Organizer)",
                    "date": row["date"],
                    "description": row["description"],
                    "amount": format_cents(row["amount_cents"]),
                    "amount_cents": row["amount_cents"],
                    "category_id": row["category_id"],
                    "category_name": row["category_name"] or "Other",
                    "category_icon": row["category_icon"] or "💡",
                    "category_color": row["category_color"] or "#6B7280",
                    "split_type": row["split_type"],
                    "notes": row["notes"],
                    "personIds": person_ids,
                    "friendIds": friend_ids,
                    "friendShare": format_cents(f_share_cents),
                    "organizerShare": format_cents(org_share_cents),
                    "splits": [
                        {
                            "person_id": s["person_id"],
                            "amount_cents": s["amount_cents"],
                            "amount": format_cents(s["amount_cents"]),
                            "share_value": s["share_value"],
                        }
                        for s in splits
                    ],
                }
                result.append(item)
            return result

    def get_expense(self, expense_id):
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            if not row:
                return None
            items = self.get_expenses(row["trip_id"])
            return next((x for x in items if x["id"] == expense_id), None)

    def add_expense(
        self,
        trip_id,
        date,
        description,
        amount,
        friend_ids,
        payer_id=0,
        category_id=None,
        split_type="equal",
        custom_splits=None,
        notes="",
        include_organizer=True,
    ):
        description = description.strip()
        if not description:
            raise ValueError("Description cannot be empty.")
        if len(description) > 100:
            raise ValueError("Description cannot exceed 100 characters.")

        amount_cents = parse_amount_to_cents(amount)
        if amount_cents <= 0 or amount_cents > 100_000_000:
            raise ValueError("Enter an amount from 0.01 to 1000000.00 with two decimal places.")

        # Validate date YYYY-MM-DD
        from datetime import datetime
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date. Use YYYY-MM-DD.")

        # Ensure friend_ids are valid in this trip
        existing_friends = {f["id"] for f in self.get_friends(trip_id)}
        for fid in friend_ids:
            if fid not in existing_friends:
                raise ValueError("One or more selected friends do not exist.")

        # Assemble participant list (0 for organizer, plus friend_ids)
        participants = list(friend_ids)
        if include_organizer and 0 not in participants:
            participants.insert(0, 0)

        if not participants:
            raise ValueError("Select at least one person who shared this expense.")

        splits_map = calculate_splits(
            amount_cents=amount_cents,
            payer_id=payer_id,
            participants=participants,
            split_type=split_type,
            custom_values=custom_splits,
        )

        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO expenses (trip_id, payer_id, date, description, amount_cents, category_id, split_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (trip_id, payer_id, date, description, amount_cents, category_id, split_type, notes.strip()))
            expense_id = cursor.lastrowid

            for pid, share_cents in splits_map.items():
                s_val = 0
                if custom_splits:
                    s_val = float(custom_splits.get(str(pid), custom_splits.get(pid, 0)))
                conn.execute("""
                    INSERT INTO expense_splits (expense_id, person_id, amount_cents, share_value)
                    VALUES (?, ?, ?, ?)
                """, (expense_id, pid, share_cents, s_val))

            conn.commit()
        return self.get_expense(expense_id)

    def update_expense(
        self,
        expense_id,
        date,
        description,
        amount,
        friend_ids,
        payer_id=0,
        category_id=None,
        split_type="equal",
        custom_splits=None,
        notes="",
        include_organizer=True,
    ):
        exp = self.get_expense(expense_id)
        if not exp:
            raise KeyError("Expense not found.")
        trip_id = exp["trip_id"]

        description = description.strip()
        if not description:
            raise ValueError("Description cannot be empty.")
        if len(description) > 100:
            raise ValueError("Description cannot exceed 100 characters.")

        amount_cents = parse_amount_to_cents(amount)
        if amount_cents <= 0 or amount_cents > 100_000_000:
            raise ValueError("Enter an amount from 0.01 to 1000000.00 with two decimal places.")

        from datetime import datetime
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date. Use YYYY-MM-DD.")

        existing_friends = {f["id"] for f in self.get_friends(trip_id)}
        for fid in friend_ids:
            if fid not in existing_friends:
                raise ValueError("One or more selected friends do not exist.")

        participants = list(friend_ids)
        if include_organizer and 0 not in participants:
            participants.insert(0, 0)

        if not participants:
            raise ValueError("Select at least one person who shared this expense.")

        splits_map = calculate_splits(
            amount_cents=amount_cents,
            payer_id=payer_id,
            participants=participants,
            split_type=split_type,
            custom_values=custom_splits,
        )

        with self.get_connection() as conn:
            conn.execute("""
                UPDATE expenses 
                SET payer_id = ?, date = ?, description = ?, amount_cents = ?, category_id = ?, split_type = ?, notes = ?
                WHERE id = ?
            """, (payer_id, date, description, amount_cents, category_id, split_type, notes.strip(), expense_id))

            conn.execute("DELETE FROM expense_splits WHERE expense_id = ?", (expense_id,))
            for pid, share_cents in splits_map.items():
                s_val = 0
                if custom_splits:
                    s_val = float(custom_splits.get(str(pid), custom_splits.get(pid, 0)))
                conn.execute("""
                    INSERT INTO expense_splits (expense_id, person_id, amount_cents, share_value)
                    VALUES (?, ?, ?, ?)
                """, (expense_id, pid, share_cents, s_val))

            conn.commit()
        return self.get_expense(expense_id)

    def delete_expense(self, expense_id):
        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            if not row:
                raise KeyError("Expense not found.")
            conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            return expense_id

    # -------------------------------------------------------------
    # PEOPLE & SETTLEMENTS & BALANCES
    # -------------------------------------------------------------
    def get_people_summary(self, trip_id):
        friends = self.get_friends(trip_id)
        expenses = self.get_expenses(trip_id)

        rows = []
        for friend in friends:
            fid = friend["id"]
            shared_items = []
            total_share_cents = 0
            total_paid_cents = 0

            for exp in expenses:
                if exp["payer_id"] == fid:
                    total_paid_cents += exp["amount_cents"]

                for s in exp["splits"]:
                    if s["person_id"] == fid:
                        total_share_cents += s["amount_cents"]
                        shared_items.append({
                            "expenseId": exp["id"],
                            "date": exp["date"],
                            "description": exp["description"],
                            "share": format_cents(s["amount_cents"]),
                            "share_cents": s["amount_cents"],
                        })

            rows.append({
                "id": fid,
                "name": friend["name"],
                "color": friend["color"],
                "total": format_cents(total_share_cents),
                "total_cents": total_share_cents,
                "paid": format_cents(total_paid_cents),
                "paid_cents": total_paid_cents,
                "net_balance": format_cents(total_paid_cents - total_share_cents),
                "net_balance_cents": total_paid_cents - total_share_cents,
                "expenses": shared_items,
            })
        return rows

    def get_settle_summary(self, trip_id):
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")

        friends = self.get_friends(trip_id)
        expenses = self.get_expenses(trip_id)
        settlements = self.get_settlements(trip_id)

        name_map = {0: trip["organizer_name"]}
        color_map = {0: "#1E293B"}
        for f in friends:
            name_map[f["id"]] = f["name"]
            color_map[f["id"]] = f["color"]

        # Track paid amounts and consumed share amounts
        paid = {0: 0}
        share = {0: 0}
        for f in friends:
            paid[f["id"]] = 0
            share[f["id"]] = 0

        trip_total_cents = 0
        organizer_share_cents = 0

        for exp in expenses:
            trip_total_cents += exp["amount_cents"]
            payer = exp["payer_id"]
            paid[payer] = paid.get(payer, 0) + exp["amount_cents"]

            for s in exp["splits"]:
                pid = s["person_id"]
                share[pid] = share.get(pid, 0) + s["amount_cents"]
                if pid == 0:
                    organizer_share_cents += s["amount_cents"]

        # Apply recorded settlements (payments made directly)
        settlement_transfers = {pid: 0 for pid in paid}
        for s in settlements:
            from_p = s["from_id"]
            to_p = s["to_id"]
            amt = s["amount_cents"]
            # from_p paid money to to_p: from_p's balance increases, to_p's decreases
            settlement_transfers[from_p] = settlement_transfers.get(from_p, 0) + amt
            settlement_transfers[to_p] = settlement_transfers.get(to_p, 0) - amt

        # Net balance = Total Paid - Total Share + Net Settlement Transfers
        net_balances = {}
        for pid in paid:
            net_balances[pid] = paid[pid] - share[pid] + settlement_transfers.get(pid, 0)

        # PRD-compatible owed map: what each friend owes the organizer in simple single-payer mode
        friend_owes_list = []
        for f in friends:
            fid = f["id"]
            friend_owes_list.append({
                "id": fid,
                "name": f["name"],
                "owes": format_cents(share.get(fid, 0)),
                "paid": format_cents(paid.get(fid, 0)),
                "net": format_cents(net_balances.get(fid, 0)),
            })

        # Calculate minimal debt transfers via min-cash-flow
        simplified = simplify_debts(net_balances)
        for t in simplified:
            t["from_name"] = name_map.get(t["from_id"], f"Person {t['from_id']}")
            t["to_name"] = name_map.get(t["to_id"], f"Person {t['to_id']}")
            t["from_color"] = color_map.get(t["from_id"], "#6B7280")
            t["to_color"] = color_map.get(t["to_id"], "#6B7280")

        return {
            "tripTotal": format_cents(trip_total_cents),
            "tripTotalCents": trip_total_cents,
            "organizerShare": format_cents(organizer_share_cents),
            "organizerShareCents": organizer_share_cents,
            "currencySymbol": trip["currency_symbol"],
            "friends": friend_owes_list,
            "balances": [
                {
                    "id": pid,
                    "name": name_map.get(pid, "Unknown"),
                    "color": color_map.get(pid, "#6B7280"),
                    "paid": format_cents(paid.get(pid, 0)),
                    "share": format_cents(share.get(pid, 0)),
                    "net": format_cents(net_balances.get(pid, 0)),
                    "net_cents": net_balances.get(pid, 0),
                    "is_organizer": pid == 0,
                }
                for pid in sorted(paid.keys())
            ],
            "simplifiedDebts": simplified,
            "isSettled": len(simplified) == 0,
        }

    # -------------------------------------------------------------
    # SETTLEMENT PAYMENTS
    # -------------------------------------------------------------
    def add_settlement(self, trip_id, from_id, to_id, amount, date, note=""):
        from_id = int(from_id)
        to_id = int(to_id)
        if from_id == to_id:
            raise ValueError("Payer and recipient cannot be the same person.")

        amount_cents = parse_amount_to_cents(amount)
        if amount_cents <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO settlements (trip_id, from_id, to_id, amount_cents, date, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (trip_id, from_id, to_id, amount_cents, date, note.strip()))
            settlement_id = cursor.lastrowid
            conn.commit()
        return self.get_settlement(settlement_id)

    def get_settlements(self, trip_id):
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT s.*, 
                       CASE WHEN s.from_id = 0 THEN (SELECT organizer_name FROM trips WHERE id = s.trip_id)
                            ELSE (SELECT name FROM friends WHERE id = s.from_id)
                       END as from_name,
                       CASE WHEN s.to_id = 0 THEN (SELECT organizer_name FROM trips WHERE id = s.trip_id)
                            ELSE (SELECT name FROM friends WHERE id = s.to_id)
                       END as to_name
                FROM settlements s
                WHERE s.trip_id = ?
                ORDER BY s.date DESC, s.id DESC
            """, (trip_id,)).fetchall()
            return [
                {
                    "id": r["id"],
                    "trip_id": r["trip_id"],
                    "from_id": r["from_id"],
                    "from_name": r["from_name"] or "Unknown",
                    "to_id": r["to_id"],
                    "to_name": r["to_name"] or "Unknown",
                    "amount": format_cents(r["amount_cents"]),
                    "amount_cents": r["amount_cents"],
                    "date": r["date"],
                    "note": r["note"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_settlement(self, settlement_id):
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM settlements WHERE id = ?", (settlement_id,)).fetchone()
            if not row:
                return None
            items = self.get_settlements(row["trip_id"])
            return next((x for x in items if x["id"] == settlement_id), None)

    def delete_settlement(self, settlement_id):
        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM settlements WHERE id = ?", (settlement_id,)).fetchone()
            if not row:
                raise KeyError("Settlement not found.")
            conn.execute("DELETE FROM settlements WHERE id = ?", (settlement_id,))
            conn.commit()
            return settlement_id

    # -------------------------------------------------------------
    # ANALYTICS & STATS
    # -------------------------------------------------------------
    def get_analytics(self, trip_id):
        expenses = self.get_expenses(trip_id)
        categories = {c["id"]: c for c in self.get_categories()}

        # Category breakdown
        cat_totals = {}
        for exp in expenses:
            cid = exp["category_id"]
            cat_totals[cid] = cat_totals.get(cid, 0) + exp["amount_cents"]

        total_trip_cents = sum(cat_totals.values())
        cat_stats = []
        for cid, cents in cat_totals.items():
            cat = categories.get(cid, {"name": "Other", "icon": "💡", "color": "#6B7280"})
            pct = round((cents / total_trip_cents * 100), 1) if total_trip_cents > 0 else 0
            cat_stats.append({
                "category_id": cid,
                "name": cat["name"],
                "icon": cat["icon"],
                "color": cat["color"],
                "amount": format_cents(cents),
                "amount_cents": cents,
                "percentage": pct,
            })
        cat_stats.sort(key=lambda x: x["amount_cents"], reverse=True)

        # Timeline daily breakdown
        daily_totals = {}
        for exp in expenses:
            d = exp["date"]
            daily_totals[d] = daily_totals.get(d, 0) + exp["amount_cents"]

        timeline = [
            {"date": d, "amount": format_cents(cents), "amount_cents": cents}
            for d, cents in sorted(daily_totals.items())
        ]

        return {
            "total_spent": format_cents(total_trip_cents),
            "total_spent_cents": total_trip_cents,
            "expense_count": len(expenses),
            "categories": cat_stats,
            "timeline": timeline,
        }

    # -------------------------------------------------------------
    # EXPORT & IMPORT
    # -------------------------------------------------------------
    def export_csv(self, trip_id):
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")
        expenses = self.get_expenses(trip_id)
        friends = {f["id"]: f["name"] for f in self.get_friends(trip_id)}
        friends[0] = trip["organizer_name"]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Date", "Description", f"Amount ({trip['currency_symbol']})",
            "Category", "Paid By", "Split Type", "Participants", "Notes",
        ])

        for exp in expenses:
            participants = ", ".join(friends.get(pid, f"ID {pid}") for pid in exp["personIds"])
            writer.writerow([
                exp["id"],
                exp["date"],
                exp["description"],
                exp["amount"],
                exp["category_name"],
                exp["payer_name"],
                exp["split_type"],
                participants,
                exp["notes"],
            ])
        return output.getvalue()

    def export_json(self, trip_id):
        trip = self.get_trip(trip_id)
        if not trip:
            raise KeyError("Trip not found.")
        return {
            "trip": trip,
            "friends": self.get_friends(trip_id),
            "expenses": self.get_expenses(trip_id),
            "settlements": self.get_settlements(trip_id),
        }

    def import_from_json(self, json_data, trip_name="Imported Trip"):
        """Import legacy trip.json format or full backup into SQLite."""
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        # Check if legacy PRD format: { "friends": [...], "expenses": [...] }
        new_trip = self.create_trip(name=trip_name)
        trip_id = new_trip["id"]

        old_to_new_friend_map = {}
        for f in json_data.get("friends", []):
            created = self.add_friend(trip_id, f["name"])
            old_to_new_friend_map[f["id"]] = created["id"]

        for e in json_data.get("expenses", []):
            mapped_friend_ids = [old_to_new_friend_map[fid] for fid in e.get("friendIds", []) if fid in old_to_new_friend_map]
            amount_str = format_cents(e["amountCents"]) if "amountCents" in e else e.get("amount", "0.00")
            self.add_expense(
                trip_id=trip_id,
                date=e["date"],
                description=e["description"],
                amount=amount_str,
                friend_ids=mapped_friend_ids,
                payer_id=0,
                include_organizer=True,
            )

        return self.get_trip(trip_id)

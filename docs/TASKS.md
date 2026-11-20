# Trip Expense Tracker — Tasks

Build order for the approved PRD and tech spec, expanded with SQLite backend and SplitTrip Pro features.

## T-01 — Project setup

- [x] **Status:** completed
- **Description:** Add the Python dependencies and a Flask page that opens with no sign-in.
- **Files:** `requirements.txt`, `app.py`, `templates/index.html`
- **Acceptance criteria:** `GET /` returns the HTML page with status 200. The page has no sign-in.
- **PRD feature:** One organizer, no accounts

## T-02 — Equal-split rule

- [x] **Status:** completed
- **Description:** Calculate each friend's share and the organizer's share in cents. Friends share equally. Leftover cents stay with the organizer.
- **Files:** `split.py`, `tests/test_split.py`
- **Acceptance criteria:** Dinner with 2 friends splits 120.00 into 40.00 each. Snacks with 1 friend splits 50.00 into 25.00. Taxi with 3 friends splits 90.00 into 22.50. An amount of 1.00 with 2 friends gives each friend 0.33 and the organizer 0.34.
- **PRD feature:** Equal split; Organizer is always included

## T-03 — JSON trip file

- [x] **Status:** completed
- **Description:** Read and write `data/trip.json`. Create the empty trip when the file is missing. A successful change rewrites the whole file.
- **Files:** `store.py`, `tests/test_api.py`
- **Acceptance criteria:** A missing file becomes `{ "nextFriendId": 1, "nextExpenseId": 1, "friends": [], "expenses": [] }`. Saving then loading returns the same friends and expenses. Ids are not reused after a delete.
- **PRD feature:** One trip, then start over

## T-04 — Add and list friends

- [x] **Status:** completed
- **Description:** Add a friend by name and list friends in file order.
- **Files:** `app.py`, `store.py`, `tests/test_api.py`
- **Acceptance criteria:** `POST /api/friends` with `{ "name": "Asha" }` returns `{ "id": 1, "name": "Asha" }` and saves the file. `GET /api/friends` returns friends in the order they were added. A blank name and a duplicate name, ignoring case, return 400 and leave the file unchanged.
- **PRD feature:** Add friends

## T-05 — Record expenses

- [x] **Status:** completed
- **Description:** Save an expense with a date, description, amount, and one or more friends. Return the equal split.
- **Files:** `app.py`, `store.py`, `tests/test_api.py`
- **Acceptance criteria:** `POST /api/expenses` for Dinner, 120.00, friends Asha and Ben, returns `friendShare` 40.00 and `organizerShare` 40.00. `GET /api/expenses` lists expenses by date, then id. An expense with no friends, a zero amount, a missing description, a bad date, or an unknown friend id returns 400 and leaves the file unchanged.
- **PRD feature:** Record an expense; Choose who shared it

## T-06 — Expenses by person and settle

- [x] **Status:** completed
- **Description:** Show each friend's expenses and the end-of-trip totals from the PRD example.
- **Files:** `app.py`, `tests/test_api.py`
- **Acceptance criteria:** After Asha, Ben, Cara, Dinner, Snacks, and Taxi, `GET /api/settle` returns Asha 62.50, Ben 62.50, Cara 47.50, organizer share 87.50, and trip total 260.00. `GET /api/people` shows the same friend totals and only the expenses each friend shared. Neither route writes the file.
- **PRD feature:** Expenses by person; Settle

## T-07 — Edit and remove

- [x] **Status:** completed
- **Description:** Rename or remove a friend, and change or remove an expense. Recalculate shares from the saved data.
- **Files:** `app.py`, `store.py`, `tests/test_api.py`
- **Acceptance criteria:** Renaming a friend does not change what they owe. Removing a friend who shares an expense with others updates `friendIds` and later settle totals. Removing the only friend on an expense returns 409 and leaves the file unchanged. Deleting an expense removes it from settle. Unknown ids return 404.
- **PRD feature:** Edit and remove

## T-08 — Start over

- [x] **Status:** completed
- **Description:** Clear the one trip back to an empty JSON document.
- **Files:** `app.py`, `store.py`, `tests/test_api.py`
- **Acceptance criteria:** `DELETE /api/trip` returns empty friend and expense lists and writes the empty document. A new friend can be added afterward and receives the next id, not a reused one.
- **PRD feature:** One trip, then start over

## T-09 — Organizer page

- [x] **Status:** completed
- **Description:** Build the single page: friends, expense form, expense list, expenses by person, settle, and start over.
- **Files:** `templates/index.html`, `static/styles.css`, `static/app.js`, `app.py`
- **Acceptance criteria:** The organizer can add 3 friends, enter 3 expenses with different subsets, and see the PRD settle totals without a second person. Each friend and expense can be edited or removed. Start over asks for confirmation, then both lists are empty. A failed request shows the error next to the form that sent it.
- **PRD feature:** One organizer, no accounts; Add friends; Record an expense; Choose who shared it; Expenses by person; Settle; One trip, then start over; Edit and remove

---

## Pro Extensions (Added Features)

## T-10 — SQLite Database Storage

- [x] **Status:** completed
- **Description:** Robust SQLite database with foreign keys, transactions, and schema management.
- **Files:** `db.py`, `tests/test_sqlite_app.py`
- **Acceptance criteria:** Tables for `trips`, `friends`, `categories`, `expenses`, `expense_splits`, `settlements`. Zero external dependencies (uses standard library `sqlite3`).

## T-11 — Multi-Trip Management

- [x] **Status:** completed
- **Description:** Create, switch, customize currency ($/€/£/₹/¥), and edit multiple trips.
- **Files:** `db.py`, `app.py`, `static/app.js`
- **Acceptance criteria:** Dropdown switches active trip, creates new trips, edits trip names and currencies.

## T-12 — Advanced Split Modes

- [x] **Status:** completed
- **Description:** Support Equal, Exact ($), Percentage (%), and Shares (Weights) splits with fair remainder rounding.
- **Files:** `split.py`, `db.py`, `app.py`, `tests/test_sqlite_app.py`
- **Acceptance criteria:** Exact amounts validate to expense total; Percentages validate to 100%; Shares allocate proportionally.

## T-13 — Multi-Payer & Debt Simplification

- [x] **Status:** completed
- **Description:** Support any friend paying for an expense. Min-cash-flow greedy algorithm computes minimal peer-to-peer transfers.
- **Files:** `split.py`, `db.py`, `app.py`, `static/app.js`
- **Acceptance criteria:** Net balances accurately computed; simplified debts show direct transfers (e.g. A pays B).

## T-14 — Settlement Payments Tracking

- [x] **Status:** completed
- **Description:** Record real repayments (Cash, Venmo, UPI), updating balances in real time with payment history.
- **Files:** `db.py`, `app.py`, `static/app.js`, `tests/test_sqlite_app.py`
- **Acceptance criteria:** Recording payment reduces debt balance until fully settled.

## T-15 — Pro UI, SVG Charts, CSV & WhatsApp Sharing

- [x] **Status:** completed
- **Description:** Modern dark/light theme, category donut chart, spending timeline, 1-click CSV export, and WhatsApp summary generator.
- **Files:** `templates/index.html`, `static/styles.css`, `static/app.js`
- **Acceptance criteria:** Interactive category donut chart, timeline bar chart, CSV download endpoint, and clipboard/WhatsApp sharing.

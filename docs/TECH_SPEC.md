# Trip Expense Tracker — Technical Specification

**Status:** Approved

## Overview

A single-organizer web application that allows one trip organizer to manage friends, record expenses with equal and custom splits, review spending by person, and settle debts at the end of a trip.
Built with Python 3, Flask, SQLite database storage, and vanilla HTML/CSS/JavaScript with zero external runtime dependencies.
Accompanied by a standalone clickable prototype in `/prototype` and an automated test suite.

## Tech Stack

- **Python 3:** Core programming language for routing, splitting algorithms, database handling, and tests.
- **Flask:** Lightweight, beginner-friendly web server for REST API endpoints and static serving.
- **SQLite 3:** Built-in standard library SQL database (`data/expenses.db`) with foreign key constraints, atomic transactions, and persistence.
- **JSON Compatibility:** `data/trip.json` retained for legacy export, import, and test verification.
- **HTML5, CSS3, & Vanilla JavaScript:** Fast, responsive frontend interface with dark/light themes, SVG charts, and zero frontend framework overhead.
- **pytest:** Command-line automated testing verifying split arithmetic, REST routes, and database operations.

## Architecture

The client browser communicates via JSON REST API endpoints with the Flask server.
The Flask application calculates shares and balances through the splitting algorithms and persists data to SQLite.

```
Browser (UI Client)  <--->  [ /prototype (Clickable HTML/CSS) ]
       |
       | JSON HTTP Requests
       v
Flask Routes (app.py)
       |
       +---> Equal & Custom Split Rules (split.py)
       |
       +---> SQLite Database Engine (db.py -> data/expenses.db)
       |
       +---> JSON Store / Export (store.py -> data/trip.json)
```

## Folder Structure

```text
AI workshop/
├── docs/
│   ├── PRD.md                  # Approved Product Requirements Document
│   ├── TECH_SPEC.md            # Technical Specification
│   └── TASKS.md                # Task list and execution log
├── prototype/                  # Clickable HTML/CSS prototype
│   ├── index.html              # Prototype entry point
│   ├── friends.html            # Screen 2: Friends management
│   ├── add-expense.html        # Screen 3: Expense entry form
│   ├── by-person.html          # Screen 4: Expenses by person breakdown
│   ├── settle.html             # Screen 5: Settle balances and start over
│   ├── style.css               # Shared prototype stylesheet
│   └── README.md               # Screen inventory & PRD story mappings
├── app.py                      # Flask routes and application factory
├── db.py                       # SQLite database manager (CRUD, splits, analytics)
├── split.py                    # Equal & custom split arithmetic & min-cash-flow
├── store.py                    # JSON persistence store
├── requirements.txt            # Flask and pytest dependencies
├── templates/
│   └── index.html              # Main application web template
├── static/
│   ├── app.js                  # Frontend client application logic
│   └── styles.css              # Responsive stylesheet (dark/light theme)
├── tests/
│   ├── test_split.py           # Split math tests
│   ├── test_api.py             # JSON API compatibility tests
│   └── test_sqlite_app.py      # SQLite CRUD, custom splits, & settlements tests
└── data/
    └── expenses.db             # SQLite database file (created at runtime)
```

## Data Model (SQLite)

### 1. `trips`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `name`: TEXT NOT NULL
- `currency_symbol`: TEXT NOT NULL DEFAULT '$'
- `currency_code`: TEXT NOT NULL DEFAULT 'USD'
- `organizer_name`: TEXT NOT NULL DEFAULT 'You (Organizer)'
- `notes`: TEXT DEFAULT ''
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `is_archived`: INTEGER DEFAULT 0

### 2. `categories`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `name`: TEXT NOT NULL UNIQUE (e.g. Food & Dining, Transport, Lodging)
- `icon`: TEXT NOT NULL (e.g. 🍕, 🚗, 🏨)
- `color`: TEXT NOT NULL

### 3. `friends`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `trip_id`: INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE
- `name`: TEXT NOT NULL
- `email`: TEXT DEFAULT ''
- `phone`: TEXT DEFAULT ''
- `color`: TEXT DEFAULT '#4F46E5'
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 4. `expenses`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `trip_id`: INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE
- `payer_id`: INTEGER NOT NULL DEFAULT 0 (0 = Organizer, or friend_id)
- `date`: TEXT NOT NULL (YYYY-MM-DD)
- `description`: TEXT NOT NULL
- `amount_cents`: INTEGER NOT NULL (stored in whole integer cents)
- `category_id`: INTEGER REFERENCES categories(id) ON DELETE SET NULL
- `split_type`: TEXT NOT NULL DEFAULT 'equal' ('equal', 'exact', 'percent', 'shares')
- `notes`: TEXT DEFAULT ''
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 5. `expense_splits`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `expense_id`: INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE
- `person_id`: INTEGER NOT NULL (0 = Organizer, or friend_id)
- `amount_cents`: INTEGER NOT NULL
- `share_value`: REAL DEFAULT 0

### 6. `settlements`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `trip_id`: INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE
- `from_id`: INTEGER NOT NULL
- `to_id`: INTEGER NOT NULL
- `amount_cents`: INTEGER NOT NULL
- `date`: TEXT NOT NULL
- `note`: TEXT DEFAULT ''
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## API Endpoints

### Friends API

#### `GET /api/friends`
- **Purpose**: List all friends in the active trip.
- **Response**:
  ```json
  {
    "friends": [
      { "id": 1, "name": "Asha" },
      { "id": 2, "name": "Ben" },
      { "id": 3, "name": "Cara" }
    ]
  }
  ```

#### `POST /api/friends`
- **Purpose**: Add a new friend by name.
- **Request**:
  ```json
  { "name": "Asha" }
  ```
- **Response**:
  ```json
  { "id": 1, "name": "Asha" }
  ```

#### `PATCH /api/friends/<id>`
- **Purpose**: Rename an existing friend.
- **Request**: `{ "name": "Asha R." }`
- **Response**: `{ "id": 1, "name": "Asha R." }`

#### `DELETE /api/friends/<id>`
- **Purpose**: Remove a friend. Returns 409 if friend is the sole participant on an expense.
- **Response**: `{ "deleted": 1 }`

---

### Expenses API

#### `GET /api/expenses`
- **Purpose**: List expenses sorted by date then ID.
- **Response**:
  ```json
  {
    "expenses": [
      {
        "id": 1,
        "date": "2026-11-20",
        "description": "Dinner",
        "amount": "120.00",
        "friendIds": [1, 2],
        "friendShare": "40.00",
        "organizerShare": "40.00"
      }
    ]
  }
  ```

#### `POST /api/expenses`
- **Purpose**: Record an expense with date, description, amount, and participants.
- **Request**:
  ```json
  {
    "date": "2026-11-20",
    "description": "Dinner",
    "amount": "120.00",
    "friendIds": [1, 2]
  }
  ```
- **Response**:
  ```json
  {
    "id": 1,
    "date": "2026-11-20",
    "description": "Dinner",
    "amount": "120.00",
    "friendIds": [1, 2],
    "friendShare": "40.00",
    "organizerShare": "40.00"
  }
  ```

---

### People & Settle API

#### `GET /api/people`
- **Purpose**: Show breakdown of expenses and share totals per friend.
- **Response**:
  ```json
  {
    "friends": [
      {
        "id": 1,
        "name": "Asha",
        "total": "62.50",
        "expenses": [
          { "expenseId": 1, "date": "2026-11-20", "description": "Dinner", "share": "40.00" },
          { "expenseId": 3, "date": "2026-11-21", "description": "Taxi", "share": "22.50" }
        ]
      }
    ]
  }
  ```

#### `GET /api/settle`
- **Purpose**: Calculate what each friend owes the organizer and trip totals.
- **Response**:
  ```json
  {
    "tripTotal": "260.00",
    "organizerShare": "87.50",
    "friends": [
      { "id": 1, "name": "Asha", "owes": "62.50" },
      { "id": 2, "name": "Ben", "owes": "62.50" },
      { "id": 3, "name": "Cara", "owes": "47.50" }
    ]
  }
  ```

#### `DELETE /api/trip`
- **Purpose**: Reset trip data back to empty.
- **Response**: `{ "friends": [], "expenses": [] }`

---

## Error Handling and Validation

| Scenario | HTTP Status | Behavior |
| :--- | :---: | :--- |
| Blank or missing name / description | 400 | Rejects request; database unchanged |
| Duplicate friend name (case-insensitive) | 400 | Returns error; database unchanged |
| Invalid amount format or amount $\le 0$ | 400 | Returns error; database unchanged |
| Invalid date format (not YYYY-MM-DD) | 400 | Returns error; database unchanged |
| Non-existent friend ID in expense | 400 | Returns error; database unchanged |
| Non-existent ID lookup | 404 | Returns `Friend not found.` or `Expense not found.` |
| Deleting friend who is sole participant | 409 | Returns 409 conflict error |

---

## Testing Approach

- **Split Arithmetic**: Integer cents calculations verifying exact PRD totals ($120 \rightarrow 40$ each; $50 \rightarrow 25$; $90 \rightarrow 22.50$; $1.00 \rightarrow 0.33 \times 2 + 0.34$ organizer).
- **End-to-End PRD Flow**: Asha, Ben, Cara seeded with Dinner, Snacks, Taxi matching $260.00$ trip total and $87.50$ organizer share.
- **Validation**: Bad dates, zero amounts, empty descriptions, duplicate names.
- **Edit & Delete**: Cascade updates and 409 prevention on sole participants.
- **Database CRUD**: SQLite table creation, custom splits (exact, percent, shares), multi-payer debt simplification, and settlements.

---

## Traceability Table

| PRD Feature | API Endpoint(s) | Table(s) / Store | Prototype Screen |
| :--- | :--- | :--- | :--- |
| **One organizer, no accounts** | `GET /` | `trips` | `index.html` |
| **Add friends** | `POST /api/friends`, `GET /api/friends` | `friends` | `friends.html` |
| **Record an expense** | `POST /api/expenses`, `GET /api/expenses` | `expenses`, `expense_splits` | `add-expense.html` |
| **Choose who shared it** | `POST /api/expenses`, `PATCH /api/expenses/<id>` | `expense_splits` | `add-expense.html` |
| **Organizer always included** | `GET /api/expenses`, `GET /api/settle` | `expenses`, `expense_splits` | `index.html`, `settle.html` |
| **Equal split** | `split.py`, `POST /api/expenses` | `expense_splits` | `index.html` |
| **Expenses by person** | `GET /api/people` | `friends`, `expenses` | `by-person.html` |
| **Settle** | `GET /api/settle` | `expenses`, `settlements` | `settle.html` |
| **One trip, then start over** | `DELETE /api/trip` | `trips`, `friends`, `expenses` | `settle.html` |
| **Edit and remove** | `PATCH /api/friends/<id>`, `DELETE /api/friends/<id>`, `PATCH /api/expenses/<id>`, `DELETE /api/expenses/<id>` | `friends`, `expenses` | `friends.html`, `index.html` |
| **Custom shares** | `POST /api/expenses` (`split_type`) | `expense_splits` | `add-expense.html` |

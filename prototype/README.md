# Trip Expense Tracker — Prototype

Clickable front-end prototype built with plain HTML, CSS, and minimal JavaScript.

## How to Run

Double-click `prototype/index.html` in any web browser, or open it directly via the file protocol:
`file:///C:/Users/USER/Downloads/AI%20workshop/prototype/index.html`

No build steps, frameworks, or web servers are required.

---

## Screen Inventory & PRD Story Mappings

| Screen File | Screen Title | PRD User Story Covered |
| :--- | :--- | :--- |
| `index.html` | Overview & Expenses | **Story 2, 4, 5, 9**: Overview of recorded bills, equal split breakdown, edit/delete actions |
| `friends.html` | Friends List | **Story 1, 9**: Add friends by name without accounts; rename or remove friends |
| `add-expense.html` | Record Expense | **Story 2, 3, 4, 5**: Record date, amount, description; select subset of friends; organizer automatically included |
| `by-person.html` | Expenses by Person | **Story 6**: Filter and inspect each individual friend's charges and shared line items |
| `settle.html` | Settle Balances & Start Over | **Story 7, 8**: Settle action showing owed amounts (PRD worked example totals); clear trip to start over |

---

## Technical Constraints Verification

- [x] Plain HTML, CSS, and vanilla JS only.
- [x] No backend, no frameworks, no database, no CDN links.
- [x] Shared `style.css` for consistent appearance.
- [x] Opens by double-clicking `index.html`.
- [x] Every screen directly traces back to an approved PRD user story.

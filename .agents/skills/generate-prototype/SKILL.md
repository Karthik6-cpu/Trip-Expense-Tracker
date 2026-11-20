---
name: generate-prototype
description: Build a clickable HTML/CSS/JS prototype in /prototype based on an approved docs/PRD.md. Uses plain HTML/CSS with no backend/database, works by double-clicking index.html, and maps screens to PRD user stories.
---

# Generate Prototype

Build a lightweight, clickable front-end prototype in the `/prototype` folder based on an approved PRD before starting any back-end development.

## Prerequisite

Check that `docs/PRD.md` exists and is approved. If it is missing, **STOP** and instruct the student to run `generate-prd` first.

## Process

1. **Read `docs/PRD.md`.** List every *Must Have* user story.
2. **Propose a screen list** (one line per screen) and a navigation flow between them. Ask the student to approve it before building.
3. **Build one HTML page per screen**, linked together so the student can click through the main flow.
4. **Use placeholder data only** (for example, `"Student Name"`, `"Sample Item"`, `"$120.00"`).
5. **If anything in the PRD is unclear or contradictory, ask.** Do not guess.

## Technical Constraints

- **Plain HTML, CSS, and minimal JavaScript only.**
- **No frameworks**, no backend server, no database, no external APIs or CDN dependencies.
- **One shared `style.css`** for a clean, consistent look across all screens.
- **Must open directly in a browser** by double-clicking `prototype/index.html` (file protocol friendly).

## Output Location

All files go in the `prototype/` directory:
```text
prototype/
├── index.html       # Primary entry screen
├── [screen-2].html  # Secondary screens linked via <a> or buttons
├── style.css        # Shared consistent stylesheet
└── README.md        # Screen inventory and PRD story mappings
```

## Quality Checklist

- [ ] Every screen maps directly to a PRD user story.
- [ ] Main user flow works end-to-end by clicking.
- [ ] No feature appears that is not defined in the PRD.
- [ ] A short `prototype/README.md` lists all screens and the PRD story each covers.

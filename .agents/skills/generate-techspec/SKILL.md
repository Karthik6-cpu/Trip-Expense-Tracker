---
name: generate-techspec
description: Generate a comprehensive technical specification in docs/TECH_SPEC.md based on approved docs/PRD.md and /prototype. Defines architecture, data models, API endpoints, error handling, test approach, and a feature traceability table.
---

# Generate Tech Spec (Technical Specification)

Generate an engineering technical specification based on an approved PRD and interactive prototype before writing application code.

## Prerequisite

Read `docs/PRD.md` and the `/prototype` folder.
- If `docs/PRD.md` is missing, **STOP** and instruct the student to run `generate-prd`.
- If the PRD and the prototype disagree, list the conflicts and ask the student which one is correct. Never resolve conflicts silently.

## Process

1. **Summarise the PRD features and prototype screens in 5 lines** to confirm understanding.
2. **Propose the tech stack** with a one-line reason for each choice. Prefer simple, widely used tools suitable for beginners.
3. **Write the specification** using the template below.
4. **Trace every table and endpoint back to a PRD feature.** Remove anything that cannot be traced directly.
5. **Ask the student to approve** before moving on to development.

---

## Spec Template

```markdown
# [Project Title] — Technical Specification

## Overview
[What is being built, in 3 lines]

## Tech Stack
- **[Tool/Language 1]**: [One-line reason]
- **[Tool/Language 2]**: [One-line reason]

## Architecture
[Short description]

[Simple ASCII or text architecture diagram]

## Folder Structure
[Full project directory tree]

## Data Model
[Tables/collections, fields, data types, and relationships]

## API Endpoints
### [Method] [Path]
- **Purpose**: [What it does]
- **Request Example**:
  \`\`\`json
  { ... }
  \`\`\`
- **Response Example**:
  \`\`\`json
  { ... }
  \`\`\`

## Error Handling and Validation
- [Key input validation rules]
- [HTTP error codes and error response format]

## Testing Approach
- [What will be tested and testing tools]

## Traceability Table
| PRD Feature | API Endpoint(s) | Table(s) / Store |
| :--- | :--- | :--- |
| [Feature Name] | [e.g. POST /api/...] | [e.g. friends] |
```

---

## Output Location

Save to `docs/TECH_SPEC.md`.

## Quality Checklist

- [ ] Every endpoint and table appears in the Traceability Table.
- [ ] No feature exists that is not in the PRD.
- [ ] Folder structure matches the chosen tech stack.
- [ ] No application code implementation is included in the specification.

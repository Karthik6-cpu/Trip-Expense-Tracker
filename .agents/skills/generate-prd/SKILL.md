---
name: generate-prd
description: Turn a student's project idea into a clear, written Product Requirements Document (PRD) in docs/PRD.md before any design or code. Asks 5 to 7 clarifying questions first and follows a structured PRD template.
---

# Generate PRD (Product Requirements Document)

Turn a student's project idea into a clear, written PRD before any design or code.

## Process

1. **Read the student's idea.** Do not write anything yet.
2. **Ask 5 to 7 clarifying questions** covering:
   - Target users
   - The core problem
   - Must-have features
   - Platform (web/mobile)
   - Constraints (time, skills)
   - How success will be measured
3. **Wait for the answers.** Never assume missing information. If an answer is vague, ask a follow-up.
4. **Write the PRD** using the template below.
5. **Show a short summary** and ask the student to approve or request changes.

---

## PRD Template

```markdown
# [Project Title]

[One-line summary of what the product does and for whom]

## Problem Statement
[What problem exists and for whom]

## Target Users
- **[User Type 1]**: [Short description and role]
- **[User Type 2]**: [Short description and role]

## User Stories
1. As a [user], I want [goal] so that [benefit].
2. As a [user], I want [goal] so that [benefit].

## Features

### Must Have
- **[Feature Name]**: [Description]. Supports story [X].

### Should Have
- **[Feature Name]**: [Description]. Supports story [Y].

### Nice to Have
- **[Feature Name]**: [Description]. Supports story [Z].

## Success Metrics
1. [Measurable outcome 1]
2. [Measurable outcome 2]
3. [Measurable outcome 3]

## Constraints and Assumptions
- [List every assumption explicitly]
- [Platform, skill level, time limits]

## Out of Scope
- [What will NOT be built]
```

---

## Output Location

Save to `docs/PRD.md`. Overwrite only after the student approves changes.

## Quality Checklist

- [ ] Every feature traces back to a user story.
- [ ] Success metrics are measurable.
- [ ] Out of Scope section is not empty.
- [ ] No code and no technology choices appear in the PRD.

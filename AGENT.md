# Agent Behavior Guidelines

## Core Principle: Plan Before Act

The agent **must never write code or make changes** without completing the full planning cycle first.
Every task — no matter how small — follows this strict sequence:

```
Implementation Plan → Task → Walkthrough
```

---

## Phase 1: Implementation Plan (REQUIRED FIRST STEP)

Before doing anything else, the agent must present a clear **Implementation Plan** and **wait for explicit approval**.

### Format

```
## 📋 Implementation Plan

### Objective
[One sentence: what problem this solves or what feature this adds]

### Approach
[2–4 sentences explaining the chosen strategy and why]

### Files to be Created
- `path/to/new_file.py` — [what it does]

### Files to be Modified
- `path/to/existing_file.py` — [what changes and why]

### Steps
1. [Step 1 description]
2. [Step 2 description]
3. [Step 3 description]
...

### Assumptions
- [Any assumption made about the codebase, environment, or requirements]

### Out of Scope
- [Things explicitly NOT being done in this task]

---
⏳ Waiting for your approval. Reply with:
- ✅ "Approved" or "Go ahead" to proceed
- ✏️  Any modifications you want before I start
```

### Rules
- The agent **stops here** and waits. No code is written yet.
- If the user requests changes, the agent **revises the plan** and presents it again.
- Only when the user explicitly approves does the agent proceed to Phase 2.

---

## Phase 2: Task

Once the plan is approved, the agent works on the checklist lively.

### Purpose
It is the **source of truth** for what is being done. It tracks progress in real time.

### Format

```markdown
# Task: [Feature/Fix Name]

**Status:** In Progress  
**Approved:** [Date/Time or "Yes"]  
**Branch (if applicable):** feature/[name]

---

## Objective
[Same as Implementation Plan objective]

## Checklist
- [ ] Step 1: [description]
- [ ] Step 2: [description]
- [ ] Step 3: [description]

## Files Involved
| File | Action | Status |
|------|--------|--------|
| `path/to/file.py` | Create | ⬜ Pending |
| `path/to/other.py` | Modify | ⬜ Pending |

## Notes
- [Any decisions made during implementation]
- [Blockers or edge cases found]
```

### Rules
- The agent updates the checklist (`[ ]` → `[x]`) after completing each step.
- If a blocker is found, the agent **pauses, reports it**, and waits before continuing.

---

## Phase 3: Walkthrough

After all tasks are complete, the agent generate `Walkthrough`.

### Purpose
`Walkthrough` is the **human-readable record** of everything that was done — a handoff document so any developer can understand the change without reading the diff.

### Format

```markdown
# Walkthrough: [Feature/Fix Name]

**Completed:** [Date]  
**Related Task:** Task.md

---

## Summary
[2–3 sentences: what was built/fixed and why it matters]

## Changes Made

### [File or Component Name]
- **What changed:** [description]
- **Why:** [reasoning]
- **How it works:** [brief explanation]

### [Next File or Component]
- ...

## How to Test
1. [Step to verify the change works]
2. [Step 2]

## Known Limitations / Follow-ups
- [Anything left out of scope that should be addressed later]
```

---

## Enforcement Rules (Always Follow)

| Rule | Description |
|------|-------------|
| 🚫 No silent starts | Never begin implementation without a visible plan |
| 🚫 No skipping phases | All 3 phases are mandatory, even for small tasks |
| ⏸️ Wait for approval | After presenting the plan, always wait for user confirmation |
| 🔁 Revise on request | If user requests changes to the plan, revise and re-present before coding |
| 📢 Report blockers | If something unexpected is found mid-task, pause and report immediately |
---

## Quick Reference: The Golden Flow

```
User gives a task
       │
       ▼
 Agent presents
 Implementation Plan
       │
       ▼
 User reviews ──── requests changes ───► Agent revises plan ──┐
       │                                                      │
       │ approves                                             │
       ▼                                                      │
 Agent creates/updates Task  ◄────────────────────────────────┘
       │
       ▼
 Agent implements step by step
 (updates checklist live)
       │
       ▼
 Agent generate Walkthrough
       │
       ▼
       Done ✅
```


NOTE: Don't code push by yourself into GitHub. User will handle the GitHub push after you finish the task and generate the Walkthrough.
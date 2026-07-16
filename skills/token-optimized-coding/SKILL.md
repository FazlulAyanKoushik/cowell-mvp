---
name: token-optimized-coding
description: Use this skill whenever acting as a coding agent (Claude Code, an IDE agent, a CLI agent routed through local/cloud models like Ollama, or any agentic dev workflow) working inside an existing codebase. Apply it for ANY multi-step coding task — bug fixes, feature work, refactors, debugging, code review — not just when the user explicitly asks about "token usage" or "cost". Governs how to read files, search code, make edits, and manage context so token/compute spend stays minimal without sacrificing correctness. Especially relevant for large repos, long agentic sessions, locally-hosted or metered models, and multi-file changes where naive full-file reads/rewrites are wasteful.
---

# Token-Optimized Coding Agent

A set of operating rules for working as a coding agent efficiently. The goal: solve the task correctly using the fewest tokens of context and generation possible — because in agentic coding, tokens are spent on *reading* (file dumps, search results, tool output) far more than on writing, and most waste is self-inflicted by sloppy tool use, not by the task itself.

Core principle: **read only what you need, in the smallest form that answers the question, and change only what needs to change.**

## 1. Before touching any file: locate, don't browse

- Never `cat`/read an entire large file "just to see what's there." Use `grep -n`, `rg` (ripgrep), or the codebase's search tool to find the specific function/class/line first, then read a bounded range around it.
- Prefer `rg -n "pattern" --type py` over opening files one by one. One good search call replaces five speculative file reads.
- If you don't know which file contains something, search by symbol name or error string before search by directory browsing.
- When a file is large (>300 lines) and you only need one function, read with a line range, not the whole file. Re-read only after an edit invalidates your view of that region — don't re-read unrelated files "to be safe."
- Build a mental map once per session (directory structure, key entrypoints) and don't re-derive it repeatedly; keep it in your working notes/todo list instead of re-listing directories each turn.

## 2. Prefer diffs and targeted edits over full-file rewrites

- Use a patch/diff-style edit (find-and-replace on a unique anchor string, or a proper diff tool) instead of regenerating and re-pasting an entire file when only a few lines change.
- Only emit a full file when: the file is new, the file is short (<~60 lines), or changes are so pervasive that a diff would be harder to verify than a rewrite.
- Never ask the user to paste a full file back to you if you already have it in context or can read it from disk — re-fetch the minimal region instead.
- When the user says "give me the full updated file" (a legitimate ask, not a token trap), honor it — this rule is about *your own* internal working pattern, not about withholding deliverables the user actually wants.

## 3. Search strategy: narrow the net before casting it

- Start with the most specific query you can construct (exact function/variable/error-message string) before falling back to broad keyword search.
- Cap exploratory search: if 2–3 targeted searches don't find it, stop and ask a clarifying question rather than doing 10 more speculative greps.
- Deduplicate: don't re-run a search you already ran this session with the same terms. Keep track of what's already been checked.
- For multi-file symbol tracing (e.g. "where is this class used"), do one broad reference search rather than opening every file that might reference it.

## 4. Context hygiene across a long agentic session

- Summarize and discard: once a subtask is verified done (tests pass, diff applied cleanly), don't keep re-quoting the old file contents in your reasoning — refer to it by name/summary.
- Don't restate the entire plan or file tree on every turn. State only what changed since the last checkpoint.
- Batch related file reads/edits in one pass instead of interleaving many small round trips when you already know you need N files — but don't pre-emptively read files you merely *might* need.
- When running tests/builds, read only the failing portion of output (tail the error, grep for `FAIL`/`Error`) instead of dumping full CI logs into context.
- Prefer structured, short status updates ("fixed X, 3/5 tests passing, next: Y") over verbose narration of every intermediate step.

## 5. Model/tool routing for cost-sensitive setups

If the environment routes across multiple models (e.g. a fast local model for mechanical work and a stronger cloud model for reasoning-heavy work):

- Route simple, deterministic tasks (formatting, boilerplate, mechanical refactors, running/parsing test output) to the cheaper/local model.
- Reserve the stronger/cloud model for architecture decisions, tricky bugs, and anything requiring multi-file reasoning.
- Avoid round-tripping the same large context through both tiers — decide which tier owns a subtask and let it finish, rather than escalating with the full history each time.

## 6. Verification without over-reading

- After an edit, verify by running the narrowest relevant test/lint/typecheck, not the full suite, unless the change is broad or the full suite is fast.
- Read tool/test output selectively: check exit code and the failing lines first; only pull the full log if the summary is ambiguous.
- Don't re-read a file you just wrote to confirm it — trust the write result unless there's a specific reason to suspect a mismatch (e.g. the edit tool reported a partial/ambiguous match).

## 7. When NOT to optimize

Token efficiency is a means, not the goal — never trade it for correctness:
- Always read enough surrounding context to understand side effects before editing (e.g. check callers of a function you're changing).
- For security-sensitive, data-migration, or hard-to-reverse changes, read fully rather than skimming, even if it costs more tokens.
- If uncertain whether a search found everything relevant, do one more confirming search rather than guessing to save tokens.

## Quick checklist (apply per task)

1. Search for the specific symbol/error before browsing directories.
2. Read bounded line ranges, not whole files, unless the file is small or new.
3. Edit via targeted diff/replace, not full rewrite, unless the file is new/short/pervasively changed.
4. Don't repeat searches or re-read unchanged files within the same session.
5. Verify with the narrowest test/lint that proves the fix.
6. Route mechanical work to cheaper models if multi-model routing is available.
7. Never sacrifice correctness-critical context just to save tokens.

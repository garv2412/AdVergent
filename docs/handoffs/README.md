# Phase handoff convention

Use one file per phase: `phase-0.md`, `phase-1.md`, etc. Keep the active handoff current; retain earlier phase records and identify later corrections explicitly.

Every handoff must contain:

1. Phase ID, date, status (in progress / complete / incomplete), and exit-gate result.
2. What changed, with relevant file links.
3. User decisions versus proposed defaults.
4. Checks/tests: exact commands, execution date, result, and scope/limitations. Explicitly list tests not run.
5. Known issues, unresolved questions, and unverified claims.
6. Next phase prerequisites and concrete starting steps.
7. Any scope/schedule changes and deviations from the plan.
8. A ready-to-use starter prompt for the next phase, also placed at the end of the final response. This does not authorize automatic advancement.

Update project status, product specification, architecture, phase plan, and AGENTS.md as applicable before closing a phase. A new chat reads the repository rather than reconstructing decisions from memory. Never put secrets in a handoff.

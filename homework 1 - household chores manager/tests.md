# Tests

Accepted scenarios to cover (proposed one-by-one, added on approval).
Each maps to plan/backlog behavior; kept only if it guards a real edge.

## Already covered (chores/tests.py, 7 tests)

- Roommate delete prunes rotation, next assignee preserved
- Roommate delete with empty rotation pauses (index reset)
- Roommate delete refused when chores reference them (history kept)
- Open ordering: overdue → due soon → no-date; OVERDUE flag shown
- Chore create validation: title / assignee / past due date
- Done/reopen lifecycle with actor + timestamps; fairness counts
- Lazy generation rotates Ana→Bo, dedupes refresh, delete stops

## Accepted (new)

1. Filter: `GET /?assignee=<Bo>` shows only Bo's open + done chores; Ana's hidden; non-numeric id ignored (unfiltered). [implemented]
2. Roommate validation: empty/blank name and duplicate name re-render with error, save nothing. [implemented]
3. Recurring validation: bad interval / no members / past next_due / empty title → error, nothing saved; valid weekly [Ana, Bo] → 302. [implemented]

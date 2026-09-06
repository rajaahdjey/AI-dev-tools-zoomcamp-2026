# Backlog — Household Chores Manager

Source: `_docs/plan.md` (Approach §1–9, Verification). Stack: Django 4.2 + SQLite, no login, no cron. Build in order; each item done = its acceptance holds.

1. **Models + migrations** (plan §8)
   - `Roommate(name unique)`; `Chore(title ≤120, notes blank, assignee FK PROTECT, status open/done, due_date nullable, source_recurring FK nullable CASCADE, created_at, done_at nullable, actor_name)`; `RecurringChore(title, notes blank, interval_days ∈ {1,7,14,30} default 7, next_due, rotation JSON ids, current_index=0)`.
   - Acceptance: `manage.py migrate` clean, no warnings.

2. **Roommates: create/list/delete** (plan §1)
   - No auth. Delete keeps done history under archived name, removes member from all rotations; rotation left empty pauses generation.
   - Acceptance: Ana/Bo creatable, listed; deleting Bo keeps their done rows, prunes rotations.

3. **Chores: create/list + due dates** (plan §2, §9)
   - Validate title non-empty, assignee exists, `due_date >= today`; invalid → re-render, no partial save. `/` sorts open overdue → due soon → no-date, then done newest-first; overdue (open + due < today) flagged; assignee filter; no reminders.
   - Acceptance: "Trash"→Ana due today listed correctly; bad form shows error, saves nothing.

4. **Done / reopen workflow** (plan §3, §4)
   - `POST /chores/<id>/done`, `POST /chores/<id>/reopen` only; no assignee edit after done except via reopen. Actor from `?as=`/form select; every change records actor + timestamp. Completing a generated instance never auto-spawns the next.
   - Acceptance: done-as-Ana empties open list with actor+timestamp; reopen-as-Bo refills it.

5. **Fairness block** (plan §5)
   - `/` shows per-roommate `done` counts (group-by assignee). No points/weighting/streaks.
   - Acceptance: after §4, block reads Ana:1 (or matching counts).

6. **Recurring templates + lazy generation** (plan §6, §9)
   - `/recurring/new` validates title, interval, ≥1 existing roommate, `next_due >= today`; `POST /recurring/<id>/delete` stops. `GET /` loop: while `next_due <= today` (cap 10): skip if open `Chore` with same source+due exists, else create with `assignee=rotation[current_index % len]`; advance index/`next_due`; save once. No cron, no skip/pause.
   - Acceptance: weekly "Bathroom" [Ana, Bo] due today → `GET /` yields Ana instance; next due cycle yields Bo; delete stops generation; refresh never duplicates.

7. **End-to-end acceptance** (plan Verification a/b/c)
   - Run the three scripted checks (chore lifecycle, overdue flag + counts, rotation Ana→Bo→stop) against `migrate + runserver`.
   - Acceptance: all three pass as written in plan.md.

## Explicitly out (never during build)

Reminders/notifications, points weighting/streaks, login/permissions, Postgres, skip/pause or recurrence edit-history.

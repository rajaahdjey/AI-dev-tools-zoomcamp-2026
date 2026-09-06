# Household Chores Manager

Shared task tracker for roommates (2–6 people): assign chores, track who did what. Simple assign + mark-done workflow, no login.

> V1 is scope only — no build yet. Agreed stack: Python + Django web app with SQLite.

## How it works

1. **Roommates:** create/list roommate names. No auth — acting user picked per-action via `?as=<roommate>` / form select. Deleting a roommate keeps their done history under archived name and removes them from recurring rotations.
2. **Chores + due dates:** create chore with title (required, max 120 chars), optional notes, assignee (required, must be existing roommate), optional due date (>= today). List shows open first (overdue → due soon → no-date), then done. Overdue = open + due < today, flagged in UI. No reminders/notifications.
3. **Workflow only:** mark `open → done`, reopen `done → open`. No assignee edit after done except via reopen. Every state change records actor + timestamp.
4. **Fairness counts:** `/` shows done-count per roommate. No points/weighting/streaks.
5. **Recurring with rotation:** `RecurringChore` template (title, interval 1/7/14/30 days default 7, next due, ordered rotation). `GET /` lazily generates due instances, rotating assignee; no cron. Delete template to stop.
6. Forms validate title non-empty, assignee/rotation exist, dates >= today; invalid → re-render with error, no partial save.

## Out of scope for v1

Due-date reminders/notifications, points weighting/streaks, login/permissions, Postgres, skip/pause or recurrence edit-history. Never add during build.

## Stack

- Python + Django (web app)
- SQLite (Django default)
- No login — pick name from roommate list

## Data model (app `chores`)

- `Roommate(name unique)`
- `Chore(title, notes blank, assignee FK Roommate PROTECT, status open/done default open, due_date nullable, source_recurring FK nullable, created_at, done_at nullable, actor_name)`
- `RecurringChore(title, notes blank, interval_days, next_due, rotation JSON list of Roommate ids, current_index)`

## Pages / routes

- `/` — open + done lists with assignee filter, fairness block, recurring section (triggers lazy generation)
- `/chores/new` — create form (+ due date)
- `POST /chores/<id>/done` — mark done
- `POST /chores/<id>/reopen` — reopen
- `/recurring/new` — create recurring template
- `POST /recurring/<id>/delete` — stop recurrence

Templates: `chores/templates/chores/` — list (+ overdue flag, fairness, recurring) + create forms with actor select.

## Getting started (build phase)

Not implemented yet. When built:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Then: create roommates Ana/Bo → create chore "Trash" assigned Ana due today → mark done as Ana → reopen as Bo. Overdue chores flag on `/`; fairness block counts done per roommate; weekly `RecurringChore` "Bathroom" rotation [Ana, Bo] generates Ana instance, then Bo on next due.

See `_docs/plan.md` for the full scoped v1 plan.

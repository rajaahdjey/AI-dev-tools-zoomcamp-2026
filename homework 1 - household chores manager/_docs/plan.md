# Household Chores Tool — Scoped v1 Plan

## Context
Homework scope for a shared household-chores manager for roommates (2–6 people): track who does what via simple assign + mark-done, with optional due dates, per-roommate done counts, and simple recurring chores with rotating assignment. V1 scope only, no build yet; agreed stack is Python + Django web app with SQLite and no login (pick name from roommate list). Reminders/notifications, points weighting, login/permissions, and Postgres are explicitly deferred.

## Answers collected
- Q1 core job → Shared task tracking (assign tasks to people, track who did what)
- Q2 users → Roommates 2–6
- Q3 platform → Python with Django (web app)
- Q4 workflow → Assign + mark done (simple)
- Q5 storage → SQLite (Django default)
- Q6 identity → No login, pick name from roommate list
- Q7 recurrence → Simple recurring with rotating assignment (lazy generation on list view, no cron)
- Q8 constraint → Just scope, no build yet
- Q9 due dates → Optional due date + overdue flag, no reminders/notifications
- Q10 fairness → Simple done-counts per roommate, no points weighting
- Q11 rotation → Recurring template rotates assignee in fixed roommate order

## Approach
Agreed v1 scope (implement later exactly as below, nothing more):
1. Manage roommates: create/list roommate names (no auth); deleting a roommate keeps their done history under archived name and removes them from recurring rotations; a rotation with zero members pauses generation.
2. Manage chores + due dates: create chore with title (required, max 120 chars), optional notes, assignee (required, must be existing roommate), optional due_date (date, >= today on create), status open/done; list open first sorted overdue → due soon → no-date, then done newest-first. Overdue = open + due_date < today, flagged in UI. No reminders/notifications.
3. Complete workflow only: mark open→done and reopen done→open; no edit of assignee after done except via reopen. Completing a generated recurring instance does not auto-create the next one; the next instance appears via lazy generation.
4. No login: acting user chosen per-action via `?as=<roommate>` / form select; every state change records actor + timestamp.
5. Fairness counts: `/` shows done-count per roommate (count of `Chore(status=done)` grouped by assignee); no points, weighting, or streaks.
6. Recurring with rotating assignment: `RecurringChore` template (title, notes, interval_days choices 1/7/14/30 default 7, next_due date, rotation ordered list of roommates, current_index). Lazy generation on `GET /`: while next_due <= today (cap 10 iterations): skip create if an open `Chore` with same source + due already exists, else create `Chore(title, notes, assignee=rotation[current_index % len], due_date=next_due, source FK)`; then current_index++, next_due += interval_days; save once. No cron/worker. Create form validates title, interval, >=1 existing roommate, next_due >= today. Delete template to stop; no skip/pause/edit-history.
7. Out of v1, never add during build: due-date reminders/notifications, points weighting/streaks, login/permissions, Postgres, skip/pause or recurrence edit-history.
8. Data model (Django, app `chores`): `Roommate(name unique)`, `Chore(title, notes blank, assignee FK Roommate PROTECT, status choices open/done default open, due_date nullable date, source_recurring FK nullable CASCADE, created_at, done_at nullable, actor_name)`, `RecurringChore(title, notes blank, interval_days, next_due date, rotation JSON list of Roommate ids in order, current_index default 0)`.
9. Pages: `/` open+done lists with assignee filter + fairness block + recurring section (GET triggers lazy generation); `/chores/new` create form (+ due_date input); `POST /chores/<id>/done` and `POST /chores/<id>/reopen`; `/recurring/new` create template; `POST /recurring/<id>/delete` to stop. Forms validate title non-empty, assignee/rotation members exist, due_date/next_due >= today; invalid → re-render with error, no partial save.

## Critical files & anchors
- `AI-dev-tools-zoomcamp-2026/README.md` — homework root; scope lives alongside (unverified — confirm before build).
- New `chores/models.py` — `Roommate`, `Chore` (+ `due_date`, `source_recurring`), `RecurringChore` as above.
- New `chores/views.py` — list (with lazy generation + fairness counts) /create/done/reopen + recurring create/delete actions.
- New `chores/urls.py` — the four chore routes above plus `/recurring/new` and `POST /recurring/<id>/delete`.
- New `chores/templates/chores/` — list (+ overdue flag, fairness block, recurring section) + create forms with actor select.

## Verification
Scope acceptance (no code yet): read this file top-to-bottom and confirm each Approach line maps to answers Q1–Q11 with no extras.
Build acceptance later: `python manage.py migrate && python manage.py runserver`, then (a) create roommates Ana/Bo, create chore "Trash" assigned Ana with due_date today, mark done as Ana, reopen as Bo — open list empties then refills; done history shows actor + timestamp; (b) set a chore due yesterday via shell/`next_due` past date → `/` flags it overdue, no notification sent; `/` fairness block shows Ana:1, Bo:0 (or matching counts); (c) create weekly `RecurringChore` "Bathroom" rotation [Ana, Bo] next_due today → `GET /` generates open Chore assigned Ana due today; advance next_due to today again → next `GET /` generates Bo instance; delete template stops generation.

## Assumptions & contingencies
- Assumes Django + SQLite acceptable for homework demo; if reviewer requires Postgres, swap `DATABASES` only, models unchanged.
- Assumes no-login acceptable; if auth required later, add Django auth and map `actor_name` to user, keep routes.
- Recurrence runs without cron by design (lazy on `GET /`, capped catch-up, dedupe on source+due); if a real scheduler is required later, move the same generation loop into a management command / periodic task, keep model and rotation semantics unchanged.

# Household Chores Tool — Scoped v1 Plan

## Context
Homework scope for a shared household-chores manager for roommates (2–6 people): track who does what via simple assign + mark-done. V1 is scope only, no build yet; agreed stack is Python + Django web app with SQLite and no login (pick name from roommate list). Recurrence and fairness/points are explicitly deferred.

## Answers collected
- Q1 core job → Shared task tracking (assign tasks to people, track who did what)
- Q2 users → Roommates 2–6
- Q3 platform → Python with Django (web app)
- Q4 workflow → Assign + mark done (simple)
- Q5 storage → SQLite (Django default)
- Q6 identity → No login, pick name from roommate list
- Q7 recurrence → Later / nice-to-have (v1 one-time only)
- Q8 constraint → Just scope, no build yet

## Approach
Agreed v1 scope (implement later exactly as below, nothing more):
1. Manage roommates: create/list roommate names (no auth); deleting a roommate keeps their done history under archived name.
2. Manage chores: create chore with title (required, max 120 chars), optional notes, assignee (required, must be existing roommate), status open/done; list open first, then done.
3. Complete workflow only: mark open→done and reopen done→open; no edit of assignee after done except via reopen.
4. No login: acting user chosen per-action via `?as=<roommate>` / form select; every state change records actor + timestamp.
5. Out of v1, never add during build: recurrence, due-date reminders/notifications, points/fairness stats, login/permissions, Postgres.
6. Data model (Django, app `chores`): `Roommate(name unique)`, `Chore(title, notes blank, assignee FK Roommate PROTECT, status choices open/done default open, created_at, done_at nullable, actor_name)`.
7. Pages: `/` open+done lists with assignee filter; `/chores/new` create form; `POST /chores/<id>/done` and `POST /chores/<id>/reopen`. Forms validate title non-empty and assignee exists; invalid → re-render with error, no partial save.

## Critical files & anchors
- `AI-dev-tools-zoomcamp-2026/README.md` — homework root; scope lives alongside (unverified — confirm before build).
- New `chores/models.py` — `Roommate`, `Chore` as above.
- New `chores/views.py` — list/create/done/reopen actions.
- New `chores/urls.py` — the four routes above.
- New `chores/templates/chores/` — list + create form with actor select.

## Verification
Scope acceptance (no code yet): read this file top-to-bottom and confirm each Approach line maps to answers Q1–Q8 with no extras.
Build acceptance later: `python manage.py migrate && python manage.py runserver`, then create roommates Ana/Bo, create chore "Trash" assigned Ana, mark done as Ana, reopen as Bo — open list empties then refills; done history shows actor + timestamp.

## Assumptions & contingencies
- Assumes Django + SQLite acceptable for homework demo; if reviewer requires Postgres, swap `DATABASES` only, models unchanged.
- Assumes no-login acceptable; if auth required later, add Django auth and map `actor_name` to user, keep routes.
- If recurrence requested later, add `Recurrence(rule, next_run)` as new model, never alter v1 `Chore` status flow.

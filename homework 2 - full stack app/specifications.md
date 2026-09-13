# Mini Kanban Board — Specifications

## 1. Overview
Mini Kanban board for managing dev tasks for a small developer group.

- Single shared board, visible to everyone (authenticated).
- `DevOps` creates tasks and assigns them.
- `Developer` works only on tasks assigned to them: move status, edit details, annotate.
- Board is classic Kanban: vertical columns per status, cards per task, drag-and-drop between columns, per-user filtering.

## 2. Goals / Non-goals
Goals:
- Shared visibility of all tasks and statuses.
- Clear ownership: every task has at most one assignee.
- Frictionless status updates via drag-and-drop + annotation.
- Enforced role permissions server-side.

Non-goals (v1):
- No sprints, epics, story points, time tracking.
- No email / Slack notifications.
- No multi-board / multi-project support.
- No admin UI for user management (seeded users only).

## 3. Roles & Access

| Capability | Everyone (authenticated viewer) | Developer | DevOps |
|---|---|---|---|
| View board, all columns, all cards | ✅ | ✅ | ✅ |
| Filter: "My tasks only" / by assignee | ✅ | ✅ | ✅ |
| Search / filter by status, priority, text | ✅ | ✅ | ✅ |
| Create task | ❌ | ❌ | ✅ |
| Assign / reassign task | ❌ | ❌ | ✅ |
| Delete task | ❌ | ❌ | ✅ |
| Move own assigned task between statuses | ❌ | ✅ (own only) | ✅ (any, to allow triage) |
| Edit title/description/priority of own task | ❌ | ✅ (own only) | ✅ (any) |
| Add comment / status note to own task | ❌ | ✅ (own only) | ✅ (any) |

Rules:
- Unassigned tasks: only DevOps can move/edit/assign. Developers have read-only.
- Developer attempting to mutate another user's task → `403`, no state change.
- All permission checks enforced on backend, not just hidden in UI.
- Viewing is never blocked: any authenticated user sees all tasks.

### Seeded identity (v1 auth)
- No full auth provider. Pre-seeded users with `id, name, role`:
  - 1x `devops` user, Nx `developer` users.
- Simple session: select user on login screen (or `X-User-Id` header for API). No passwords in v1.
- Future: replace with real login without changing permission matrix.

## 4. Board Structure

Fixed columns (left → right), each a vertical swimlane:
1. `Backlog`
2. `To Do`
3. `In Progress`
4. `In Review`
5. `Done`

Rules:
- Every task is in exactly one column (`status` field).
- Columns show card count. Empty columns show empty-state text.
- `Done` is terminal but reversible (can drag back out).
- v1: no WIP limits, no custom columns.

## 5. Task Model

```text
Task {
  id: string (uuid)
  title: string (required, max 120 chars)
  description: string (optional, markdown-ish plain text)
  status: Backlog | To Do | In Progress | In Review | Done
  assigneeId: string | null  (single developer; null = unassigned)
  priority: Low | Medium | High
  createdBy: string (devops user id)
  createdAt: timestamp
  updatedAt: timestamp
  comments: Comment[]
}

Comment {
  id: string
  taskId: string
  authorId: string
  body: string (required, max 2000 chars)
  createdAt: timestamp
}
```

Validation:
- `title` required, non-blank.
- `assigneeId`, if set, must reference an existing `developer` user.
- `status` transitions unrestricted in v1 (any → any), recorded in activity.
- `comments` append-only; no edit/delete in v1 (keeps audit simple).

Activity (derived, not user-editable):
- Log `created, assigned, moved, edited, commented` with `actor, timestamp, from → to`. Shown in card detail drawer. Can be derived from `updatedAt` + comments in minimal v1, or a separate `events` table.

## 6. Functional Requirements

### 6.1 Viewing
- `FR-1`: Board loads all tasks grouped by `status`, sorted by `priority desc, updatedAt desc` within a column.
- `FR-2`: Card face shows: title, assignee avatar/initials, priority badge, comment count, short description snippet.
- `FR-3`: Click card → detail drawer/modal: full description, assignee, status, priority, comments thread, activity.
- `FR-4`: Board auto-refreshes after any mutation (optimistic UI with server reconciliation acceptable).

### 6.2 Create / Assign (DevOps only)
- `FR-5`: DevOps "New task" button → form: title*, description, assignee (dropdown of developers + Unassigned), priority (default Medium), initial status (default Backlog).
- `FR-6`: DevOps can reassign from card detail or drag assignee control; reassignment updates `assigneeId` + logs event.
- `FR-7`: DevOps can delete task (with confirm). Deleted task disappears for all.
- `FR-8`: Create validation errors shown inline; failed create does not add a card.

### 6.3 Move / Update (Developer, own tasks only)
- `FR-9`: Developer drags own card between columns → `PATCH /tasks/:id { status }`. Card animates to new column; failure rolls back + toast.
- `FR-10`: Developer cannot drag others' cards: card is `draggable=false`, shows "Assigned to X" lock hint.
- `FR-11`: Developer can edit title/description/priority of own tasks via detail drawer. Edits to others' tasks are disabled in UI and rejected (`403`) by API.
- `FR-12`: Unassigned cards are not draggable/editable by developers.

### 6.4 Filter & Focus
- `FR-13`: "My tasks only" toggle: dims/hides cards not assigned to current user. Default OFF (everyone sees everything).
- `FR-14`: Assignee filter (dropdown / avatar row): show one, several, or all developers.
- `FR-15`: Text search over title + description; priority filter; status is implicit via columns.
- `FR-16`: Filters combine (AND) and survive status moves without resetting. "Clear filters" resets.
- `FR-17`: Filter state is per-session, not persisted server-side.

### 6.5 Annotate
- `FR-18`: Any user with edit rights on a task (owner-dev or DevOps) can add a comment/status note from detail drawer.
- `FR-19`: Comments show author + timestamp, newest last. No edit/delete in v1.
- `FR-20`: Adding a comment bumps `updatedAt` but does not change `status` unless explicitly moved.

## 7. UI / UX
- Layout: header (app title, user switcher, My-tasks toggle, search, New-task button if DevOps) + horizontal row of 5 vertical columns.
- Columns: header (name + count), scrollable card list, drop highlight on drag-over.
- Cards: compact, clickable, visual priority cue (color/bar), assignee chip.
- Detail drawer: right-side panel, editable fields gated by permission, comments thread + input at bottom.
- Responsive: columns horizontally scrollable on narrow screens; minimum usable at 360px.
- Feedback: toasts for create/move/assign errors (especially `403` with "Only DevOps can create tasks" / "Only assignee can move this task").
- Accessibility: drag-and-drop has equivalent "Move to ▸" dropdown in detail drawer for keyboard users.

## 8. API (suggested)
```
GET    /api/tasks                    → list all (with assignee, commentCount)
GET    /api/tasks?assigneeId=&q=&priority=
GET    /api/tasks/:id                → detail + comments + activity
POST   /api/tasks                    → DevOps only { title, description, assigneeId, priority, status }
PATCH  /api/tasks/:id                → { title?, description?, priority?, status?, assigneeId? }
                                       DevOps: any field; Developer: own tasks, all except reassign-to-other? (v1: dev cannot change assigneeId at all)
POST   /api/tasks/:id/comments       → { body }
DELETE /api/tasks/:id                → DevOps only
GET    /api/users                    → id, name, role (for assignee dropdown / filters)
```

Auth: current user via session / `X-User-Id` header in v1. Every mutating endpoint checks role + ownership.

Error contract: `4xx` JSON `{ error: string }`; `403` for permission, `404` for missing task, `422` for validation.

## 9. Persistence & Stack
- Any simple full-stack setup acceptable, e.g. React/Vite + Node/Express + SQLite/Postgres, or Next.js + Prisma.
- Single `tasks`, `users`, `comments` (+ optional `events`) tables. Seed: 1 DevOps + 3–4 developers + 8–12 sample tasks across columns.
- No real-time websockets required in v1; refetch on mutation + manual refresh is enough.

## 10. Acceptance Criteria
- [ ] Anyone logged in sees all 5 columns and all cards.
- [ ] DevOps can create a task, assign it, and it appears in the right column for everyone.
- [ ] Developer A cannot move/edit/comment on Developer B's task (`403`, UI disabled, no state change).
- [ ] Developer can drag own card to a new column; reload preserves the move.
- [ ] "My tasks only" hides other developers' cards without affecting stored data.
- [ ] Detail drawer allows owner-dev to edit description and add a comment; comment persists after reload.
- [ ] Unassigned task is read-only for developers, fully manageable by DevOps.
- [ ] Direct API calls bypassing the UI still enforce the same permission matrix.

## 11. Edge Cases
- Reassigned while being edited → last write wins; reassignment logged.
- Deleted task with open drawer → drawer shows "Task deleted", closes on confirm.
- Drag onto same column → no-op, no API call.
- Empty assignee dropdown (no developers seeded) → create allows Unassigned only.
- Long titles/descriptions truncated on card, full in drawer.

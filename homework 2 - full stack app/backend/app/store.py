"""In-memory store: users, tasks, sessions + seed data.

Business rules mirror frontend/src/services/mockBackend.js exactly:
DevOps can do anything; developers only their own assigned tasks;
unassigned tasks are read-only for developers; only DevOps can
assign/reassign, create, or delete.
"""

from __future__ import annotations

import time
import uuid

from . import auth
from .models import (
    COMMENT_MAX,
    DESCRIPTION_MAX,
    PRIORITIES,
    STATUSES,
    TITLE_MAX,
    ApiError,
    Comment,
    CreateTask,
    Event,
    Task,
    UpdateTask,
    User,
    UserInDB,
)

SEED_PASSWORD = "password123"

_SEED_USERS = [
    ("u-devops", "Mira Shah", "devops"),
    ("u-ana", "Ana Ruiz", "developer"),
    ("u-ben", "Ben Carter", "developer"),
    ("u-cleo", "Cleo Park", "developer"),
    ("u-dev", "Dev Patel", "developer"),
]


def now_ms() -> int:
    return int(time.time() * 1000)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _seed_tasks(base: int) -> list[dict]:
    h = 3600_000
    d = 24 * h

    def ev(id: str, type: str, actor: str, at: int, detail: str = "") -> dict:
        return {"id": id, "type": type, "actorId": actor, "at": at, "detail": detail}

    def cm(id: str, author: str, at: int, body: str) -> dict:
        return {"id": id, "authorId": author, "at": at, "body": body}

    return [
        {
            "id": "t-101", "title": "Set up CI pipeline for staging",
            "description": "GitHub Actions: lint, test, build on every PR. Cache node_modules.",
            "status": "Backlog", "priority": "High", "assigneeId": None,
            "createdBy": "u-devops", "createdAt": base - 4 * d, "updatedAt": base - 4 * d,
            "comments": [],
            "events": [ev("e-101-1", "created", "u-devops", base - 4 * d, "Created in Backlog")],
        },
        {
            "id": "t-102", "title": "Design empty states for board columns",
            "description": "Figma first, then implement. Keep copy short and friendly.",
            "status": "Backlog", "priority": "Low", "assigneeId": "u-cleo",
            "createdBy": "u-devops", "createdAt": base - 3 * d, "updatedAt": base - 2 * d,
            "comments": [cm("c-102-1", "u-cleo", base - 2 * d, "Drafted two variants, will attach screenshots.")],
            "events": [
                ev("e-102-1", "created", "u-devops", base - 3 * d, "Created in Backlog"),
                ev("e-102-2", "assigned", "u-devops", base - 3 * d, "Assigned to Cleo Park"),
            ],
        },
        {
            "id": "t-103", "title": "API: GET /api/tasks with filters",
            "description": "Support assigneeId, q, priority query params. Paginate later.",
            "status": "To Do", "priority": "High", "assigneeId": "u-ana",
            "createdBy": "u-devops", "createdAt": base - 3 * d, "updatedAt": base - 26 * h,
            "comments": [],
            "events": [
                ev("e-103-1", "created", "u-devops", base - 3 * d, "Created in Backlog"),
                ev("e-103-2", "moved", "u-devops", base - 26 * h, "Backlog → To Do"),
            ],
        },
        {
            "id": "t-104", "title": "Auth: user switcher + X-User-Id header",
            "description": "Temporary v1 auth. Document swap path to real login.",
            "status": "To Do", "priority": "Medium", "assigneeId": "u-ben",
            "createdBy": "u-devops", "createdAt": base - 3 * d, "updatedAt": base - 30 * h,
            "comments": [],
            "events": [ev("e-104-1", "created", "u-devops", base - 3 * d, "Created in To Do")],
        },
        {
            "id": "t-105", "title": "Card drag-and-drop between columns",
            "description": "HTML5 DnD with keyboard fallback (Move-to dropdown). Roll back on 403.",
            "status": "In Progress", "priority": "High", "assigneeId": "u-ana",
            "createdBy": "u-devops", "createdAt": base - 5 * d, "updatedAt": base - 5 * h,
            "comments": [cm("c-105-1", "u-ana", base - 8 * h, "DnD working, adding drop highlight + rollback toast.")],
            "events": [
                ev("e-105-1", "created", "u-devops", base - 5 * d, "Created in Backlog"),
                ev("e-105-2", "moved", "u-ana", base - 2 * d, "Backlog → In Progress"),
                ev("e-105-3", "commented", "u-ana", base - 8 * h, "Added a status note"),
            ],
        },
        {
            "id": "t-106", "title": "Task detail drawer with comments",
            "description": "Right slide-over: editable fields, comment thread, activity log.",
            "status": "In Progress", "priority": "Medium", "assigneeId": "u-dev",
            "createdBy": "u-devops", "createdAt": base - 4 * d, "updatedAt": base - 3 * h,
            "comments": [cm("c-106-1", "u-dev", base - 6 * h, "Drawer layout done, wiring permission-gated inputs.")],
            "events": [
                ev("e-106-1", "created", "u-devops", base - 4 * d, "Created in To Do"),
                ev("e-106-2", "moved", "u-dev", base - 1 * d, "To Do → In Progress"),
            ],
        },
        {
            "id": "t-107", "title": "Fix overdue badge timezone bug",
            "description": "Dates render a day off in IST. Normalize to UTC before formatting.",
            "status": "In Progress", "priority": "Medium", "assigneeId": "u-ben",
            "createdBy": "u-devops", "createdAt": base - 2 * d, "updatedAt": base - 10 * h,
            "comments": [],
            "events": [ev("e-107-1", "created", "u-devops", base - 2 * d, "Created in In Progress")],
        },
        {
            "id": "t-108", "title": "Write permission tests for PATCH /tasks/:id",
            "description": "Dev A cannot edit Dev B tasks (403). DevOps can edit any.",
            "status": "In Review", "priority": "High", "assigneeId": "u-cleo",
            "createdBy": "u-devops", "createdAt": base - 6 * d, "updatedAt": base - 12 * h,
            "comments": [cm("c-108-1", "u-cleo", base - 12 * h, "Ready for review: 6 cases, all passing locally.")],
            "events": [
                ev("e-108-1", "created", "u-devops", base - 6 * d, "Created in To Do"),
                ev("e-108-2", "moved", "u-cleo", base - 12 * h, "In Progress → In Review"),
            ],
        },
        {
            "id": "t-109", "title": "Seed demo users + sample tasks script",
            "description": "1 DevOps, 4 developers, 10 tasks across all columns.",
            "status": "Done", "priority": "Low", "assigneeId": "u-dev",
            "createdBy": "u-devops", "createdAt": base - 7 * d, "updatedAt": base - 2 * d,
            "comments": [cm("c-109-1", "u-devops", base - 2 * d, "Seed looks good.")],
            "events": [
                ev("e-109-1", "created", "u-devops", base - 7 * d, "Created in Backlog"),
                ev("e-109-2", "moved", "u-devops", base - 2 * d, "In Review → Done"),
            ],
        },
        {
            "id": "t-110", "title": "Responsive columns for mobile",
            "description": "Horizontal scroll under 1100px. Min usable width 360px.",
            "status": "Done", "priority": "Medium", "assigneeId": "u-ana",
            "createdBy": "u-devops", "createdAt": base - 6 * d, "updatedAt": base - 3 * d,
            "comments": [],
            "events": [ev("e-110-1", "created", "u-devops", base - 6 * d, "Created in Done")],
        },
        {
            "id": "t-111", "title": "Document backend swap (mock → REST)",
            "description": "One-file swap: replace src/api/mockApi.js with fetch calls. Keep signatures.",
            "status": "To Do", "priority": "Low", "assigneeId": None,
            "createdBy": "u-devops", "createdAt": base - 1 * d, "updatedAt": base - 1 * d,
            "comments": [],
            "events": [ev("e-111-1", "created", "u-devops", base - 1 * d, "Created in To Do")],
        },
    ]


class InMemoryStore:
    def __init__(self, seed: bool = True):
        self.users: dict[str, UserInDB] = {}
        self.tasks: dict[str, Task] = {}
        self.tokens: dict[str, str] = {}  # token -> user id
        if seed:
            self.seed()

    # ----- seed -----

    def seed(self) -> None:
        self.users = {
            id: UserInDB(id=id, name=name, role=role, password_hash=auth.hash_password(SEED_PASSWORD))
            for id, name, role in _SEED_USERS
        }
        base = now_ms()
        self.tasks = {t["id"]: Task(**t) for t in _seed_tasks(base)}
        self.tokens = {}

    # ----- sessions -----

    def create_session(self, token: str, user_id: str) -> None:
        self.tokens[token] = user_id

    def get_user_by_token(self, token: str) -> UserInDB | None:
        user_id = self.tokens.get(token)
        return self.users.get(user_id) if user_id else None

    def delete_session(self, token: str) -> None:
        self.tokens.pop(token, None)

    # ----- users -----

    def list_users(self) -> list[User]:
        return [u.public() for u in self.users.values()]

    def get_user(self, user_id: str) -> UserInDB | None:
        return self.users.get(user_id)

    def get_developer_or_throw(self, user_id: str) -> UserInDB:
        u = self.users.get(user_id)
        if u is None or u.role != "developer":
            raise ApiError(422, "Assignee must be a developer.")
        return u

    # ----- permissions -----

    @staticmethod
    def can_mutate(task: Task, actor: User) -> bool:
        if actor.role == "devops":
            return True
        return task.assigneeId is not None and task.assigneeId == actor.id

    def assert_can_mutate(self, task: Task, actor: User) -> None:
        if self.can_mutate(task, actor):
            return
        if auth.is_devops(actor):
            raise ApiError(403, "Not allowed.")
        if task.assigneeId is None:
            raise ApiError(403, "Only DevOps can modify unassigned tasks.")
        raise ApiError(403, "Only the assignee can modify this task.")

    # ----- tasks -----

    def list_tasks(self) -> list[Task]:
        return list(self.tasks.values())

    def get_task_or_throw(self, task_id: str) -> Task:
        t = self.tasks.get(task_id)
        if t is None:
            raise ApiError(404, "Task not found. It may have been deleted.")
        return t

    def create_task(self, input: CreateTask, actor: User) -> Task:
        if not auth.is_devops(actor):
            raise ApiError(403, "Only DevOps can create tasks.")
        title = (input.title or "").strip()
        if not title:
            raise ApiError(422, "Title is required.")
        if len(title) > TITLE_MAX:
            raise ApiError(422, "Title must be 120 characters or fewer.")
        if input.status not in STATUSES:
            raise ApiError(422, "Invalid status.")
        if input.priority not in PRIORITIES:
            raise ApiError(422, "Invalid priority.")
        if input.assigneeId is not None:
            self.get_developer_or_throw(input.assigneeId)
        if len(input.description or "") > DESCRIPTION_MAX:
            raise ApiError(422, "Description is too long.")
        now = now_ms()
        t = Task(
            id=_new_id("t"),
            title=title,
            description=input.description or "",
            status=input.status,
            assigneeId=input.assigneeId,
            priority=input.priority,
            createdBy=actor.id,
            createdAt=now,
            updatedAt=now,
            comments=[],
            events=[Event(id=_new_id("e"), type="created", actorId=actor.id, at=now,
                           detail=f"Created in {input.status}")],
        )
        self.tasks[t.id] = t
        return t

    def update_task(self, task_id: str, patch: UpdateTask, actor: User) -> Task:
        t = self.get_task_or_throw(task_id)

        if "assigneeId" in patch.model_fields_set and patch.assigneeId != t.assigneeId:
            if not auth.is_devops(actor):
                raise ApiError(403, "Only DevOps can assign tasks.")
            if patch.assigneeId is not None:
                self.get_developer_or_throw(patch.assigneeId)
            t.assigneeId = patch.assigneeId
            t.updatedAt = now_ms()
            name = self.users[patch.assigneeId].name if patch.assigneeId else "Unassigned"
            self._log(t, "assigned", actor.id, f"Assigned to {name}")

        wants_scalar = any(
            getattr(patch, f) is not None for f in ("title", "description", "priority", "status")
        )
        if wants_scalar:
            self.assert_can_mutate(t, actor)

        if patch.title is not None:
            title = patch.title.strip()
            if not title:
                raise ApiError(422, "Title is required.")
            if len(title) > TITLE_MAX:
                raise ApiError(422, "Title must be 120 characters or fewer.")
            if title != t.title:
                t.title = title
                t.updatedAt = now_ms()
                self._log(t, "edited", actor.id, "Edited title")
        if patch.description is not None and patch.description != t.description:
            if len(patch.description) > DESCRIPTION_MAX:
                raise ApiError(422, "Description is too long.")
            t.description = patch.description
            t.updatedAt = now_ms()
            self._log(t, "edited", actor.id, "Edited description")
        if patch.priority is not None and patch.priority != t.priority:
            if patch.priority not in PRIORITIES:
                raise ApiError(422, "Invalid priority.")
            t.priority = patch.priority
            t.updatedAt = now_ms()
            self._log(t, "edited", actor.id, f"Priority → {patch.priority}")
        if patch.status is not None and patch.status != t.status:
            if patch.status not in STATUSES:
                raise ApiError(422, "Invalid status.")
            from_status = t.status
            t.status = patch.status
            t.updatedAt = now_ms()
            self._log(t, "moved", actor.id, f"{from_status} → {patch.status}")
        return t

    def add_comment(self, task_id: str, body: str, actor: User) -> Comment:
        t = self.get_task_or_throw(task_id)
        self.assert_can_mutate(t, actor)
        text = (body or "").strip()
        if not text:
            raise ApiError(422, "Comment cannot be empty.")
        if len(text) > COMMENT_MAX:
            raise ApiError(422, "Comment must be 2000 characters or fewer.")
        c = Comment(id=_new_id("c"), authorId=actor.id, at=now_ms(), body=text)
        t.comments.append(c)
        t.updatedAt = now_ms()
        self._log(t, "commented", actor.id, "Added a status note")
        return c

    def delete_task(self, task_id: str, actor: User) -> None:
        if not auth.is_devops(actor):
            raise ApiError(403, "Only DevOps can delete tasks.")
        if task_id not in self.tasks:
            raise ApiError(404, "Task not found. It may have been deleted.")
        del self.tasks[task_id]

    @staticmethod
    def _log(task: Task, type: str, actor_id: str, detail: str) -> None:
        task.events.append(Event(id=_new_id("e"), type=type, actorId=actor_id, at=now_ms(), detail=detail))

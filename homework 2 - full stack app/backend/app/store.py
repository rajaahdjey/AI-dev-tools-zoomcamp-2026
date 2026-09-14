"""SQLAlchemy-backed store with the same API/semantics the mock defined.

Business rules: DevOps can do anything; developers only their own assigned
tasks; unassigned tasks are read-only for developers; only DevOps can
assign/reassign, create, or delete.

Sessions (bearer tokens) stay in memory on purpose: they are ephemeral and
die with the process / on reseed, while board data persists in the DB.
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from . import auth
from .db import Base, create_engine_for_url, session_factory
from .db_models import CommentRow, EventRow, TaskRow, UserRow
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

DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///./kanban.db"

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


def _user_model(row: UserRow) -> UserInDB:
    return UserInDB(id=row.id, name=row.name, role=row.role, password_hash=row.password_hash)


def _task_model(row: TaskRow) -> Task:
    comments = sorted(row.comments, key=lambda c: (c.at, c.id))
    events = sorted(row.events, key=lambda e: (e.at, e.id))
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        status=row.status,
        assigneeId=row.assignee_id,
        priority=row.priority,
        createdBy=row.created_by,
        createdAt=row.created_at,
        updatedAt=row.updated_at,
        comments=[Comment(id=c.id, authorId=c.author_id, at=c.at, body=c.body) for c in comments],
        events=[
            Event(id=e.id, type=e.type, actorId=e.actor_id, at=e.at, detail=e.detail) for e in events
        ],
    )


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


class SqlAlchemyStore:
    def __init__(self, seed: bool = True, database_url: str | None = None):
        self.database_url = database_url or os.environ.get(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)
        self.engine = create_engine_for_url(self.database_url)
        Base.metadata.create_all(self.engine)
        self._factory = session_factory(self.engine)
        self.tokens: dict[str, str] = {}  # token -> user id (ephemeral)
        if seed:
            self.ensure_seeded()

    def close(self) -> None:
        self.engine.dispose()

    @contextmanager
    def _db(self) -> Iterator[Session]:
        s = self._factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # ----- seed -----

    def ensure_seeded(self) -> None:
        # Boot must never wipe user data: only a fresh database (no users —
        # users can never be deleted via the API) gets the demo seed.
        # Explicit reseeds (admin reset) call seed() directly.
        with self._db() as s:
            fresh = s.query(UserRow.id).first() is None
        if fresh:
            self.seed()

    def seed(self) -> None:
        with self._db() as s:
            s.query(EventRow).delete()
            s.query(CommentRow).delete()
            s.query(TaskRow).delete()
            s.query(UserRow).delete()
            for id, name, role in _SEED_USERS:
                s.add(UserRow(id=id, name=name, role=role,
                              password_hash=auth.hash_password(SEED_PASSWORD)))
            base = now_ms()
            for t in _seed_tasks(base):
                row = TaskRow(
                    id=t["id"], title=t["title"], description=t["description"],
                    status=t["status"], assignee_id=t["assigneeId"], priority=t["priority"],
                    created_by=t["createdBy"], created_at=t["createdAt"], updated_at=t["updatedAt"],
                )
                for c in t["comments"]:
                    row.comments.append(CommentRow(
                        id=c["id"], task_id=t["id"], author_id=c["authorId"], at=c["at"], body=c["body"]))
                for e in t["events"]:
                    row.events.append(EventRow(
                        id=e["id"], task_id=t["id"], type=e["type"], actor_id=e["actorId"],
                        at=e["at"], detail=e["detail"]))
                s.add(row)
        self.tokens = {}

    # ----- sessions (in-memory, ephemeral) -----

    def create_session(self, token: str, user_id: str) -> None:
        self.tokens[token] = user_id

    def get_user_by_token(self, token: str) -> UserInDB | None:
        user_id = self.tokens.get(token)
        return self.get_user(user_id) if user_id else None

    def delete_session(self, token: str) -> None:
        self.tokens.pop(token, None)

    # ----- users -----

    def list_users(self) -> list[User]:
        with self._db() as s:
            rows = s.query(UserRow).order_by(UserRow.id).all()
            return [_user_model(r).public() for r in rows]

    def get_user(self, user_id: str) -> UserInDB | None:
        with self._db() as s:
            row = s.get(UserRow, user_id)
            return _user_model(row) if row else None

    def get_developer_or_throw(self, user_id: str) -> UserInDB:
        u = self.get_user(user_id)
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
        with self._db() as s:
            rows = s.query(TaskRow).order_by(TaskRow.created_at, TaskRow.id).all()
            return [_task_model(r) for r in rows]

    def get_task_or_throw(self, task_id: str) -> Task:
        with self._db() as s:
            row = s.get(TaskRow, task_id)
            if row is None:
                raise ApiError(404, "Task not found. It may have been deleted.")
            return _task_model(row)

    def _row_or_throw(self, s: Session, task_id: str) -> TaskRow:
        row = s.get(TaskRow, task_id)
        if row is None:
            raise ApiError(404, "Task not found. It may have been deleted.")
        return row

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
        with self._db() as s:
            row = TaskRow(
                id=_new_id("t"), title=title, description=input.description or "",
                status=input.status, assignee_id=input.assigneeId, priority=input.priority,
                created_by=actor.id, created_at=now, updated_at=now,
            )
            row.events.append(EventRow(
                id=_new_id("e"), task_id=row.id, type="created",
                actor_id=actor.id, at=now, detail=f"Created in {input.status}"))
            s.add(row)
            s.flush()
            return _task_model(row)

    def update_task(self, task_id: str, patch: UpdateTask, actor: User) -> Task:
        with self._db() as s:
            row = self._row_or_throw(s, task_id)

            if "assigneeId" in patch.model_fields_set and patch.assigneeId != row.assignee_id:
                if not auth.is_devops(actor):
                    raise ApiError(403, "Only DevOps can assign tasks.")
                if patch.assigneeId is not None:
                    self.get_developer_or_throw(patch.assigneeId)
                row.assignee_id = patch.assigneeId
                row.updated_at = now_ms()
                name = "Unassigned"
                if patch.assigneeId is not None:
                    assignee = s.get(UserRow, patch.assigneeId)
                    name = assignee.name if assignee else patch.assigneeId
                self._log(s, row, "assigned", actor.id, f"Assigned to {name}")

            wants_scalar = any(
                getattr(patch, f) is not None for f in ("title", "description", "priority", "status")
            )
            if wants_scalar:
                self.assert_can_mutate(_task_model(row), actor)

            if patch.title is not None:
                title = patch.title.strip()
                if not title:
                    raise ApiError(422, "Title is required.")
                if len(title) > TITLE_MAX:
                    raise ApiError(422, "Title must be 120 characters or fewer.")
                if title != row.title:
                    row.title = title
                    row.updated_at = now_ms()
                    self._log(s, row, "edited", actor.id, "Edited title")
            if patch.description is not None and patch.description != row.description:
                if len(patch.description) > DESCRIPTION_MAX:
                    raise ApiError(422, "Description is too long.")
                row.description = patch.description
                row.updated_at = now_ms()
                self._log(s, row, "edited", actor.id, "Edited description")
            if patch.priority is not None and patch.priority != row.priority:
                if patch.priority not in PRIORITIES:
                    raise ApiError(422, "Invalid priority.")
                row.priority = patch.priority
                row.updated_at = now_ms()
                self._log(s, row, "edited", actor.id, f"Priority → {patch.priority}")
            if patch.status is not None and patch.status != row.status:
                if patch.status not in STATUSES:
                    raise ApiError(422, "Invalid status.")
                from_status = row.status
                row.status = patch.status
                row.updated_at = now_ms()
                self._log(s, row, "moved", actor.id, f"{from_status} → {patch.status}")
            s.flush()
            return _task_model(row)

    def add_comment(self, task_id: str, body: str, actor: User) -> Comment:
        with self._db() as s:
            row = self._row_or_throw(s, task_id)
            self.assert_can_mutate(_task_model(row), actor)
            text = (body or "").strip()
            if not text:
                raise ApiError(422, "Comment cannot be empty.")
            if len(text) > COMMENT_MAX:
                raise ApiError(422, "Comment must be 2000 characters or fewer.")
            c = CommentRow(id=_new_id("c"), task_id=row.id, author_id=actor.id,
                           at=now_ms(), body=text)
            row.comments.append(c)
            row.updated_at = now_ms()
            self._log(s, row, "commented", actor.id, "Added a status note")
            s.flush()
            return Comment(id=c.id, authorId=c.author_id, at=c.at, body=c.body)

    def delete_task(self, task_id: str, actor: User) -> None:
        if not auth.is_devops(actor):
            raise ApiError(403, "Only DevOps can delete tasks.")
        with self._db() as s:
            row = self._row_or_throw(s, task_id)
            s.delete(row)  # comments/events cascade

    @staticmethod
    def _log(_s: Session, row: TaskRow, type: str, actor_id: str, detail: str) -> None:
        # Append via the relationship (not session.add): the events collection
        # may already be loaded in this session, and must include the new row.
        row.events.append(EventRow(id=_new_id("e"), task_id=row.id, type=type,
                           actor_id=actor_id, at=now_ms(), detail=detail))

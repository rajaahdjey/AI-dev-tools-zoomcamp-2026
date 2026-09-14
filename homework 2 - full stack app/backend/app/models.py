"""Pydantic schemas + domain constants shared by store, auth, and routers.

Validation limits mirror frontend/src/services/mockBackend.js so the real
backend accepts/rejects exactly what the mock did.
"""

from __future__ import annotations


class ApiError(Exception):
    """Domain error rendered as ``{"error": message}`` with ``status``."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


STATUSES = ["Backlog", "To Do", "In Progress", "In Review", "Done"]
PRIORITIES = ["Low", "Medium", "High"]

TITLE_MAX = 120
DESCRIPTION_MAX = 5000
COMMENT_MAX = 2000

from pydantic import BaseModel, Field  # noqa: E402


class User(BaseModel):
    id: str
    name: str
    role: str  # "devops" | "developer"


class UserInDB(User):
    password_hash: str

    def public(self) -> User:
        return User(id=self.id, name=self.name, role=self.role)


class Comment(BaseModel):
    id: str
    authorId: str
    at: int  # unix ms
    body: str


class Event(BaseModel):
    id: str
    type: str  # created | assigned | moved | edited | commented
    actorId: str
    at: int  # unix ms
    detail: str = ""


class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str = "Backlog"
    assigneeId: str | None = None
    priority: str = "Medium"
    createdBy: str
    createdAt: int
    updatedAt: int
    comments: list[Comment] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)


class CreateTask(BaseModel):
    title: str = ""
    description: str = ""
    assigneeId: str | None = None
    priority: str = "Medium"
    status: str = "Backlog"


class UpdateTask(BaseModel):
    # All-optional: None means "not provided", except assigneeId where
    # presence is checked via model_fields_set (null clears the assignee).
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    assigneeId: str | None = None


class CreateComment(BaseModel):
    body: str = ""


class LoginRequest(BaseModel):
    userId: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class Error(BaseModel):
    error: str

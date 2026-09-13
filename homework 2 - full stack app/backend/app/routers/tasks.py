from fastapi import APIRouter, Depends, Request, Response

from .. import auth
from ..models import Comment, CreateComment, CreateTask, Task, UpdateTask, User

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def list_tasks(request: Request, _user: User = Depends(auth.get_current_user)) -> list[Task]:
    return request.app.state.store.list_tasks()


@router.post("", response_model=Task, status_code=201)
def create_task(
    body: CreateTask, request: Request, user: User = Depends(auth.get_current_user)
) -> Task:
    return request.app.state.store.create_task(body, user)


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: str, request: Request, _user: User = Depends(auth.get_current_user)) -> Task:
    return request.app.state.store.get_task_or_throw(task_id)


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: str, body: UpdateTask, request: Request, user: User = Depends(auth.get_current_user)
) -> Task:
    return request.app.state.store.update_task(task_id, body, user)


@router.delete("/{task_id}", status_code=204, response_class=Response)
def delete_task(
    task_id: str, request: Request, user: User = Depends(auth.get_current_user)
) -> Response:
    request.app.state.store.delete_task(task_id, user)
    return Response(status_code=204)


@router.post("/{task_id}/comments", response_model=Comment, status_code=201)
def add_comment(
    task_id: str, body: CreateComment, request: Request, user: User = Depends(auth.get_current_user)
) -> Comment:
    return request.app.state.store.add_comment(task_id, body.body, user)

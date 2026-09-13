from fastapi import APIRouter, Depends, Request

from .. import auth
from ..models import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[User])
def get_users(request: Request, _user: User = Depends(auth.get_current_user)) -> list[User]:
    return request.app.state.store.list_users()

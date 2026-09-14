from fastapi import APIRouter, Depends, Request, Response

from .. import auth
from ..models import ApiError, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset", status_code=204, response_class=Response)
def reset_demo(request: Request, user: User = Depends(auth.get_current_user)) -> Response:
    """Reseed the in-memory demo data. DevOps only; clears all sessions."""
    if not auth.is_devops(user):
        raise ApiError(403, "Only DevOps can reset the demo.")
    request.app.state.store.seed()
    return Response(status_code=204)

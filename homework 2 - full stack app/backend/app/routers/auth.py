from fastapi import APIRouter, Depends, Request, Response

from .. import auth
from ..models import ApiError, LoginRequest, TokenResponse, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    store = request.app.state.store
    user = store.get_user(body.userId)
    if user is None or not auth.verify_password(body.password, user.password_hash):
        raise ApiError(401, "Invalid user ID or password.")
    token = auth.create_token()
    store.create_session(token, user.id)
    return TokenResponse(access_token=token, user=user.public())


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    request: Request,
    _user: User = Depends(auth.get_current_user),
    token: str = Depends(auth.get_current_token),
) -> Response:
    request.app.state.store.delete_session(token)
    return Response(status_code=204)

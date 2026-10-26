import logging
import re
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from starlette import status
from starlette.templating import Jinja2Templates

from game_engine.i18n.languages import get_supported_languages
from game_engine.session import Session, SessionException, session_manager
from web.user_db import authenticate, create_user, get_user_by_name

log = logging.getLogger(__name__)

SESSION_COOKIE = "sessionID"
_valid_username = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
MIN_PASSWORD_LENGTH = 8

user_router = APIRouter(
    prefix="/user"
)
templates = Jinja2Templates(directory="web/templates")


def set_session_cookie(request: Request, response: Response, session_id: str):
    # httponly: page scripts can not read the session id.
    # samesite=lax: other sites can not make the browser POST to us with the cookie attached.
    # secure: only sent over https (when the site is served over https).
    response.set_cookie(key=SESSION_COOKIE, value=session_id,
                        httponly=True, samesite="lax", secure=request.url.scheme == "https",
                        max_age=int(session_manager.time_out.total_seconds()))


def require_session(session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)) -> Session:
    session = session_manager.get_active_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in.")
    return session


def _login_page(request: Request, session: Optional[Session], register_error: Optional[str] = None,
                status_code: int = status.HTTP_200_OK):
    context = {"request": request,
               "session": session,
               "register_error": register_error,
               "supported_languages": sorted(get_supported_languages(), key=lambda x: x[1].lower())
               }
    return templates.TemplateResponse(request, "login.html", context, status_code=status_code)


@user_router.get("/login_page")
def index(request: Request, session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)):
    return _login_page(request, session_manager.get_active_session(session_id))


@user_router.post('/login')
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Logs in the user provided by form_data.username (or email) and form_data.password.
    A session id is stored in a cookie.
    """
    user = authenticate(form_data.username, form_data.password)
    if user is None:
        log.info("Failed login: user=%s", form_data.username)
        return JSONResponse({"detail": "Invalid username or password."}, status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        session_id = session_manager.create_session(user.username)
    except SessionException as e:
        return JSONResponse({"detail": e.user_message}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    response = JSONResponse({"user_name": user.username})
    set_session_cookie(request, response, session_id)
    return response


@user_router.post('/logout')
def logout(session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)):
    session_manager.end_session(session_id)
    response = JSONResponse({"detail": "Logged out."})
    response.delete_cookie(SESSION_COOKIE)
    return response


@user_router.post('/register')
def register(request: Request,
             username: str = Form(),
             email: str = Form(),
             password: str = Form(),
             language: str = Form(default="ENG")):
    def fail(message: str):
        return _login_page(request, None, register_error=message, status_code=status.HTTP_400_BAD_REQUEST)

    username = username.strip()
    if not _valid_username.match(username):
        return fail("Usernames are 3 to 32 letters, numbers, '-' or '_'.")
    if "@" not in email:
        return fail("That does not look like an e-mail address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        return fail(f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters.")
    if language not in {code for code, _ in get_supported_languages()}:
        language = "ENG"

    try:
        user = create_user(username, email.strip(), password, language_code=language)
        session_id = session_manager.create_session(user.username)
    except IntegrityError:
        return fail("That username or e-mail is already registered.")
    except SessionException as e:
        return fail(e.user_message)

    response = RedirectResponse("/user/login_page", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookie(request, response, session_id)
    return response


@user_router.get('/{username}')
def read_user(username: str, session: Session = Depends(require_session)):
    """
    Shows information about the user, only available to the user themselves.
    """
    user = get_user_by_name(username)
    if user is None or user.username != session.user_name:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You shall not pass with out the secret code.")

    return {"email": user.email, "language": user.language_code, "account_created": user.created}

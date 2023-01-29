import datetime
import logging
import textwrap
import traceback
from operator import itemgetter
from typing import Optional

import fastapi
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login.exceptions import InvalidCredentialsException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from game_engine.i18n.languages import get_supported_languages
from game_engine.session import SessionManager
from web.user_db import get_user_by_name, verify_password, manager, create_user


user_router = APIRouter(
    prefix="/user"
)
templates = Jinja2Templates(directory="web/templates")


@user_router.post("/show_session/")
def show_cookie(response: Response, session_id: Optional[str] = Cookie(default=None, alias="sessionID")):
    d = {"session id": session_id}

    if (session := SessionManager.get_active_session(session_id)) is not None:
        d["user_name"] = session.user_name

    d["sessions"] = [str(s) for s in SessionManager._sessions]

    return d


@user_router.get("/login_page")
def index(request: Request, session_id: Optional[str] = Cookie(default=None, alias="sessionID")):
    session = SessionManager.get_active_session(session_id)
    context = {"request": request,
               "session": session,
               "supported_languages": sorted(get_supported_languages(), key=lambda x: x[1].lower())
               }

    return templates.TemplateResponse("login.html", context)


@user_router.post('/login')
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Logs in the user provided by form_data.username and form_data.password.
    A session id is stored in a cookie.
    TODO: need someone who know more about internet security to improve this.
    """
    print("----------------------------------------------------------")
    print("----------------------------------------------------------")
    print("-                    In login form                       -")
    print("----------------------------------------------------------")
    print("----------------------------------------------------------")
    user = get_user_by_name(form_data.username)
    if user is None:
        raise InvalidCredentialsException

    if not user.can_login():
        raise InvalidCredentialsException

    if not verify_password(form_data.password, user.pw_hash):
        raise InvalidCredentialsException

    try:
        from web.chosm import load_game
        print("\n-----------------------------")
        print("User logging in: user=" + user.username)
        session_id = SessionManager.create_session(user.username, load_game=load_game)
        # print("  - all sessions: " + ", ".join([str(s) for s in SessionManager._sessions]))
        print(f"New Session id created : user={user.username}, session={session_id}")
        print("-----------------------------\n")

    except Exception as e:
        traceback.print_exc()
        logging.error(f"Error logging in user: user={user.username}, error='{str(e)}'")
        print(f"Error logging in user: user={user.username}, error='{str(e)}'")
        print("-----------------------------\n")
        raise InvalidCredentialsException

    # response = RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    html = """
            <script type="text/javascript">;
            closeNav();
            location.reload();
            </script>
            """
    html = textwrap.dedent(html)
    response = HTMLResponse(html)
    response.set_cookie(key="sessionID", value=session_id)
    return response


@user_router.post('/logout')
def logout(session_id: Optional[str] = Cookie(default=None, alias="sessionID")):
    print("----------------------------------------------------------")
    print("----------------------------------------------------------")
    print("-                    In logout                           -")
    print("----------------------------------------------------------")
    print("----------------------------------------------------------")
    session = SessionManager.get_active_session(session_id)
    if session is not None:
        session.close()
    return "done"


@user_router.post('/register')
async def register(request: Request):
    form_data = await request.form()
    print()
    print("Register new user:")
    print("   - form data: ", form_data)
    username = form_data["username"]
    email = form_data["email"]
    pw = form_data["password"]

    try:
        user = create_user(username, email, pw)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user data not valid")


        session_id = SessionManager.create_session(user.username)
        response = fastapi.responses.RedirectResponse('/', status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="sessionID", value=session_id)
        return response

    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="username already exists")






@user_router.get('/{username}')
def read_user(username, active_user=Depends(manager)):
    """
    Shows information about the user
    """
    user = get_user_by_name(username)

    if user is None or (user.username != active_user.username):
        raise HTTPException("You shall not pass with out the secret code.")

    # Only allow admins and oneself to access this information

    return {"email": user.email, "language": user.language_code, "account_created": user.created}

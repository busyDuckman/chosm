from operator import itemgetter

import fastapi
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login.exceptions import InvalidCredentialsException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from game_engine.i18n.languages import get_supported_languages
from web.user_db import get_user_by_name, verify_password, manager, create_user

# from app.db import get_session
# from app.db.actions import get_user_by_name
# from app.models.auth import Token
# from app.security import verify_password, manager

user_router = APIRouter(
    prefix="/user"
)
templates = Jinja2Templates(directory="web/templates")

@user_router.post("/get_session/")
def cookie(response: Response):
    response.set_cookie(key="mysession", value="1242r", )
    return {"message": "Wanna cookie?"}


@user_router.get("/")
def index(request: Request):
    context = {"request": request,
               "supported_languages": sorted(get_supported_languages(), key=lambda x: x[1].lower())
               }

    return templates.TemplateResponse("login.html", context)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@user_router.post('/login', response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Logs in the user provided by form_data.username and form_data.password
    """
    user = get_user_by_name(form_data.username)
    if user is None:
        raise InvalidCredentialsException

    if not verify_password(form_data.password, user.password):
        raise InvalidCredentialsException

    token = manager.create_access_token(data={'sub': user.username})
    return Token(access_token=token, token_type='bearer')


@user_router.post('/register')
async def register(request: Request):
    form_data = await request.form()
    print("--------------------request.form: ", form_data)
    username = form_data["username"]
    email = form_data["email"]
    pw = form_data["password"]

    try:
        if create_user(username, email, pw):
            # return {"detail": "Successfully registered", "username": username}
            return fastapi.responses.RedirectResponse(
                '/user',
                status_code=status.HTTP_302_FOUND)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="username already exists")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user data not valid")



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

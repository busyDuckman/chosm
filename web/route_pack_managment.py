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
from fastapi.responses import RedirectResponse, ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from game_engine.i18n.languages import get_supported_languages
from game_engine.session import SessionManager
from web.user_db import get_user_by_name, verify_password, manager, create_user

from web.server_data import ServerData

packs_router = APIRouter(
    prefix="/pack_management"
)

templates = Jinja2Templates(directory="web/templates")

@packs_router.get("/available", response_class=ORJSONResponse)
def list_packs(session_id: Optional[str] = Cookie(default=None, alias="sessionID")):

    if (session := SessionManager.get_active_session(session_id)) is None:
        return ORJSONResponse({}, status_code=status.HTTP_401_UNAUTHORIZED)

    session.user_name
    packs = sorted(list(ServerData.resource_packs.keys()))
    return ORJSONResponse(packs)


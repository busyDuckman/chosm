from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from game_engine.session import Session
from web.route_user import require_session
from web.server_data import ServerData

packs_router = APIRouter(
    prefix="/pack_management"
)


@packs_router.get("/available", response_class=ORJSONResponse)
def list_packs(session: Session = Depends(require_session)):
    packs = sorted(list(ServerData.resource_packs.keys()))
    return ORJSONResponse(packs)

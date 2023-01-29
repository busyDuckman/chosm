import logging
import os
from typing import List, Dict, NamedTuple, Optional

import xxhash
from fastapi import FastAPI, Request, Cookie
from fastapi.responses import FileResponse, HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_utils.tasks import repeat_every
from starlette import status
from starlette.responses import RedirectResponse

from chosm.dynamic_file_manager import DynamicFileManager
from chosm.game_constants import AssetTypes
from chosm.resource_pack import ResourcePack
from game_engine.game_state import GameState
from game_engine.session import Session, SessionManager
from game_engine.single_vanishing_point_painting import SingleVanishingPointPainting
from game_engine.world import World

from web.route_user import user_router

logging.basicConfig(level=logging.WARNING)

# fastAPI data
app = FastAPI()
app.mount("/web/static", StaticFiles(directory="web/static"), name="static")
app.include_router(user_router)
templates = Jinja2Templates(directory="web/templates")

# CHOSM data
resource_folder = ""
resource_packs: Dict[str, ResourcePack] = {}
chosm_version = "0.05"

dynamic_folder = ""
dyna_file_manager: DynamicFileManager = None


def save_game(user_name, game_state: GameState):
    pass


def load_game(user_name) -> GameState:
    mam5_pack: ResourcePack = resource_packs['dark-cccur-darkside-pc-dos']
    mam5_world = mam5_pack.load_world("main_world")
    return GameState(mam5_world, mam5_pack)


@app.on_event("startup")
async def startup_event():
    global resource_folder, resource_packs, dynamic_folder, dyna_file_manager
    print("CWD: " + os.getcwd())

    resource_folder = "game_files/baked"
    assert os.path.exists(resource_folder)

    for d in os.scandir(resource_folder):
        rp = ResourcePack(d.path)
        resource_packs[rp.name] = rp

    dynamic_folder = "game_files/dynamic_files"
    assert os.path.exists(dynamic_folder)
    dyna_file_manager = DynamicFileManager(dynamic_folder)

    # create an initial session
    # print(resource_packs)
    mam5_pack: ResourcePack = resource_packs['dark-cccur-darkside-pc-dos']
    mam5_world = mam5_pack.load_world("main_world")

    debug_session: Session = Session("test_user", os.urandom(32), GameState(mam5_world, mam5_pack))


@repeat_every(seconds=30)
def remove_expired_tokens_task() -> None:
    SessionManager.tick()


@app.get("/")
async def root(request: Request, session_id: Optional[str] = Cookie(default=None, alias="sessionID")):
    print("Session: " + str(session_id))
    user_name = None
    if (session := SessionManager.get_active_session(session_id)) is not None:
        user_name = session.user_name

    context = dict(version=chosm_version,
                   request=request,
                   user_name=user_name)

    return templates.TemplateResponse("landing_page.html", context)


@app.get("/api/resource-management/packs", response_class=ORJSONResponse)
async def manage_packs():
    global resource_folder, resource_packs

    packs = sorted(list(resource_packs.keys()))
    return ORJSONResponse(packs)


# @app.post("/api/resource-management/packs", response_class=ORJSONResponse)
# async def add_resource_pack(request: Request, pack_name):
#
#     rp = ResourcePackInfo(self.slug, "duckman", False)
#     rp.is_private = True
#     rp.author_info = "Developed by New World Computing, not in the public domain. Used here for research purposes only."
#     rp.save_info_file(bake_path)


@app.get('/api/resource-management/packs/{pack_name}/assets', response_class=ORJSONResponse)
async def manage_assets(pack_name: str, glob: str = None):
    global resource_folder, resource_packs

    files = resource_packs[pack_name].list_assets(glob)
    files = sorted(list(files))
    return ORJSONResponse(files)


@app.get('/api/resource-management/packs/{pack_name}/assets/{asset_name}/files')
async def manage_asset_files(pack_name, asset_name):
    global resource_folder, resource_packs

    path = resource_packs[pack_name].get_asset_path(asset_name)
    files = os.listdir(path)
    return ORJSONResponse(files)


@app.get("/download/resource-packs/{pack_name}/by_slug/{asset_slug}/{file_name}")
async def get_file(pack_name, asset_slug, file_name):
    global resource_folder, resource_packs
    pack = resource_packs[pack_name]
    file_path = pack[asset_slug].get_file_path(file_name)
    return FileResponse(path=file_path)


@app.get("/download/resource-packs/{pack_name}/by_type/{asset_type}/by_name/{asset_name}/{file_name}")
async def get_file(pack_name, asset_type, asset_name, file_name):
    global resource_folder, resource_packs
    pack = resource_packs[pack_name]
    file_path = pack[asset_type, asset_name].get_file_path(file_name)
    return FileResponse(path=file_path)


# ----------------------------------------------------------------------------------------------------------------------
@app.post("/editor/main/{pack_name}/{asset_slug}")
@app.get("/editor/main/")
@app.get("/editor/main/{pack_name}")
@app.get("/editor/main/{pack_name}/{asset_slug}")
async def editor_view(request: Request, pack_name=None, asset_slug=None, sort_on="name"):
    glob_exp = None
    # glob_exp = session.get("glob_exp", None)
    if request.method == "POST":
        form_data = await request.form()
        print("request.form: ", form_data)
        glob_exp = form_data["glob-epr"]
        glob_exp = None if len(glob_exp.strip()) == 0 else glob_exp
        # session["glob_exp"] = glob_exp if glob_exp is not None else ''
        print("Server POST ->", glob_exp)

    # print(pack_name, asset_name)
    packs = sorted(list(resource_packs.keys()))
    pack = None
    resources = {}
    if pack_name is not None:
        pack = resource_packs[pack_name]
        resources = pack.get_assets(glob_exp)

    if sort_on == "name":
        # ugly little oneliner: works because dict preserves insertion order
        resources = dict(sorted(resources.items(), key=lambda x: x[1].name))

    context = dict(packs=packs, pack=pack, pack_name=pack_name,
                   glob_exp=glob_exp,
                   resources=resources, asset_slug=asset_slug,
                   request=request)

    return templates.TemplateResponse("editor.html", context)


@app.get("/editor/asset/{pack_name}/{asset_slug}")
async def edit_asset_view(request: Request, pack_name, asset_slug):
    print("edit_asset_view")
    pack = resource_packs[pack_name]
    asset_rec = pack[asset_slug]

    context = dict(request=request,
                   pack=pack,
                   pack_name=pack_name,
                   asset_rec=asset_rec,
                   asset_slug=asset_rec.slug)

    return templates.TemplateResponse(f'edit_{asset_rec.asset_type_as_string}.html', context)


# ----------------------------------------------------------------------------------------------------------------------
@app.get("/game/main")
async def game_view(request: Request, session_id: Optional[str] = Cookie(default=None, alias="sessionID")):
    game_state = current_map = pack_name = pack = None

    session = SessionManager.get_active_session(session_id)
    if session is not None:
        game_state = session.game_state
        current_map = session.game_state.current_map
        pack_name = game_state.pack.name
        pack = game_state.pack

    context = dict(request=request,
                   pack=pack, pack_name=pack_name,
                   session=session, game_state=game_state, current_map=current_map)

    return templates.TemplateResponse(f'world_view.html', context)


@app.get("/download/ground_mask/{size_x}/{size_y}/{steps_fwd}/{steps_right}")
async def ground_mask(steps_fwd, steps_right,
                      view_dist=5, size_x=1280, size_y=720,
                      horizon_screen_ratio=0.5,
                      local_tile_ratio=0.9,
                      bird_eye_vs_worm_eye=0):

    # get file name
    txt_fwd = "BF"[steps_fwd > 0] + str(abs(steps_fwd))
    txt_right = "LR"[steps_right > 0] + str(abs(steps_right))
    h = xxhash.xxh64((horizon_screen_ratio, local_tile_ratio, bird_eye_vs_worm_eye)).hexdigest()

    file = f"{txt_fwd}_{txt_right}_{h}.webp"
    fmt = f"{size_x}_{size_y}_{view_dist}_sharp"
    path, is_valid = dyna_file_manager.querey(["ground_mask", fmt], file)

    # regen file
    if not is_valid:
        svp_composer = SingleVanishingPointPainting([], [], size=size,
                                                    bird_eye_vs_worm_eye=bird_eye_vs_worm_eye, view_dist=view_dist,
                                                    horizon_screen_ratio=horizon_screen_ratio,
                                                    local_tile_ratio=local_tile_ratio)

        img = svp_composer.draw_mask(steps_fwd, steps_right)
        img.save(path)

    # done
    return FileResponse(path=path)








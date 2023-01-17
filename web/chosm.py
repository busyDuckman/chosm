import logging
import os
from typing import List, Dict, NamedTuple

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from chosm.game_constants import AssetTypes
from chosm.resource_pack import ResourcePack
from game_engine.game_state import GameState
from game_engine.session import Session
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

sessions: dict[str, Session] = {}


@app.on_event("startup")
async def startup_event():
    global resource_folder, resource_packs
    print("CWD: " + os.getcwd())

    resource_folder = "game_files/baked"
    assert os.path.exists(resource_folder)

    for d in os.scandir(resource_folder):
        rp = ResourcePack(d.path)
        resource_packs[rp.name] = rp

    # create an initial session
    # print(resource_packs)
    mam5_pack: ResourcePack = resource_packs['dark-cccur-darkside-pc-dos']
    mam5_world = mam5_pack.load_world("main_world")

    debug_session: Session = Session("test_user", GameState(mam5_world))
    sessions["debug_session"] = debug_session


@app.get("/")
async def root(request: Request):
    context = dict(version=chosm_version,
                   request=request)

    return templates.TemplateResponse("landing_page.html", context)


@app.get("/api/resource-management/packs", response_class=ORJSONResponse)
async def manage_packs():
    global resource_folder, resource_packs

    packs = sorted(list(resource_packs.keys()))
    return ORJSONResponse(packs)


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
async def game_view(request: Request):
    session: Session = sessions["debug_session"]
    game_state = session.game_state
    current_map = session.game_state.current_map
    context = dict(request=request, session=session, game_state=game_state, current_map=current_map)

    return templates.TemplateResponse(f'world_view.html', context)

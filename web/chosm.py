import asyncio
import datetime
import logging
import os
import struct
from typing import List, Dict, NamedTuple, Optional

import xxhash
import urllib.parse

from PIL import Image
from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import FileResponse, HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_utils.tasks import repeat_every
from slugify import slugify
from starlette import status
from starlette.responses import RedirectResponse, PlainTextResponse

from chosm.asset_record import AssetRecord
from chosm.dynamic_file_manager import DynamicFileManager
from chosm.game_constants import AssetTypes
from chosm.resource_pack import ResourcePack
from game_engine.game_state import GameState, GameAction
from game_engine.map import Map
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

default_svp_composer: SingleVanishingPointPainting = None


def save_game(user_name, game_state: GameState):
    pass


def load_game(user_name) -> GameState:
    # TODO: for now just create a new game
    mam5_pack: ResourcePack = resource_packs['dark-cccur-darkside-pc-dos']
    mam5_world = mam5_pack.load_world("main_world")
    return GameState(mam5_world, mam5_pack)


@app.on_event("startup")
async def startup_event():
    global resource_folder, resource_packs, dynamic_folder, dyna_file_manager, default_svp_composer
    print("CWD: " + os.getcwd())

    default_svp_composer = SingleVanishingPointPainting([], [], size=(1920, 1024),  # not 1080, see rendering_layout.md
                                                        view_dist=5,
                                                        horizon_screen_ratio=0.5,
                                                        local_tile_ratio=0.9,
                                                        bird_eye_vs_worm_eye=0)

    resource_folder = "game_files/baked"
    assert os.path.exists(resource_folder)

    for d in os.scandir(resource_folder):
        rp = ResourcePack(d.path)
        resource_packs[rp.name] = rp

    dynamic_folder = "game_files/dynamic_files"
    assert os.path.exists(dynamic_folder)
    exp_timestamp = datetime.datetime.fromisoformat("2023-02-10").timestamp()
    dyna_file_manager = DynamicFileManager(dynamic_folder,
                                           expiration_time_stamp=exp_timestamp)

    # create an initial session
    # print(resource_packs)
    mam5_pack: ResourcePack = resource_packs['dark-cccur-darkside-pc-dos']
    mam5_world = mam5_pack.load_world("main_world")

    debug_session: Session = Session("test_user", os.urandom(32), GameState(mam5_world, mam5_pack))

    # disable logs the flood the console
    class EndpointFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.getMessage().find("GET /download/resource-packs") == -1

    # Filter out /endpoint
    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


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


@app.get("/download/css_cache/patched/{pack_name}/{asset_slug}/patched_animation.css")
async def load_and_patch_css_file(request: Request, pack_name, asset_slug):
    """
    This endpoint is designed to be called from inside a jinja2 template.
    It patches a css file resolving paths to actual server locations.

    The reason for existence is only concerned with compiling uber .css files for entire resource packs,
    see: resource_pack_css_download

    The provided endpoint is just to facilitate testing and development.
    :param pack_name:
    :param asset_slug:
    :param base_url: The new base ure for all url('') imports
    :return:
    """

    sprite_css_url = request.url_for('get_file', pack_name=pack_name, asset_slug=asset_slug, file_name='_animation.css')
    global_css_url = request.url_for('resource_pack_css_download', pack_name=pack_name)
    sprite_css_url = urllib.parse.urlparse(sprite_css_url).path
    global_css_url = urllib.parse.urlparse(global_css_url).path
    rel_path = os.path.relpath(sprite_css_url, global_css_url)
    # print(" sprite_css_url:", sprite_css_url)
    # print(" global_css_url:", global_css_url)
    # print("       rel_path:", rel_path)
    rel_path = os.path.split(rel_path)[0]
    # print("       rel_path:", rel_path)
    sprite_css_path = os.path.split(sprite_css_url)[0]

    css_file_path = resource_packs[pack_name][asset_slug].get_file_path('_animation.css')
    old_tokens = ["url('", 'url("']
    new_tokens = [f"url('{sprite_css_path}/", f'url("{sprite_css_path}/']
    with open(css_file_path, "rt") as f:
        css = f.read()
        for old_token, new_token in zip(old_tokens, new_tokens):
            css = css.replace(old_token, new_token)
    #
    # return PlainTextResponse(css + "\n")
    return css


@app.get("/download/css_cache/asset_packs/whole/{pack_name}.css")
@app.get("/download/css_cache/asset_packs/for_map/{pack_name}/{map_name}.css")
async def resource_pack_css_download(request: Request,
                                     pack_name: str,
                                     map_name: str = None):
    """
    This endpoint is called at the beginning of a rendered page.
    It creates a single .css file that has every sprite of a specified map / role bundled into it.

    This single .css is compiled from hundreds of .css files (one per game sprite, because the animation is done in css).

    The alternative approach would be only including the .css files needed for the scene.

    There are some pro's / cons to this approach.

    pro's:
        - Embedding in the .html response just one .css file reduces per query server overhead and message length.
        - Development is easier, you can just bring up a sprite as logic dictates, without having to ensure it's css
         is specified in the header. This makes html template logic a lot easier.

    con's:
        - The browser will attempt to download many sprite animation files (eg: _anim_idle.png) in the resource pack.
        - AFAIK: This results in many image files being downloaded on first query, because the browser does not do
          lazy loading. It seems different browsers handle this differently, it could:
            - Render the scene with images not yet downloaded
            - Defer rendering the scene until all images are downloaded
            - Prioritise images needed now and render the scene promptly, while downloading
              other images in the background.

    This approach has broad implications on server and browser performance that I haven't load tested.
    :param pack_name: the name of the resource pack
    :param map_name: if present loads just the sprites in the maps luts. Can be a map name, or its slug.
    """

    # TODO: This seems to work, but I have suspicions that it needs more testing.
    # TODO: Sometimes the browser seems to cache this, and other times the endpoint gets called again.
    #       If the file is updated, the browser of course is happy with its cache.
    #       But if the file is not updated, the browser hits this endpoint for a new copy.

    pack = resource_packs[pack_name]
    last_pack_modification = pack.get_modification_time()

    # setup where the cached copy will go
    if map_name is None:
        file_name = pack_name + ".css"
        categories = ["pack_css_cache"]
    else:
        file_name = map_name + ".css"
        categories = ["map_css_cache", pack_name]

    # check for ached copy
    path, is_valid = dyna_file_manager.query(categories, file_name, expiration_time=last_pack_modification)

    if not is_valid:
        print("##########################################################\n")
        print(f"#         Regenerating {file_name}\n")
        print("##########################################################\n")

        # find sprites
        if map_name is None:
            sprites = pack.get_assets_by_type(AssetTypes.SPRITE).values()
        else:
            sprites = pack.get_sprites_for_map(map_name)

        # get, and patch, all the css files
        awaitables = [load_and_patch_css_file(request, pack_name, spite.slug) for spite in sprites]
        css = await asyncio.gather(*awaitables)
        css = "\n".join(css)

        # save cached copy
        with open(path, "wt") as f:
            f.write(css)
        dyna_file_manager.invalidate_cache(["pack_css_cache"], file_name)

    # done
    response = FileResponse(path=path)
    # calling this valid for 2.5 hours; the hope being that a browser will just see this css include and
    # be happy with what it has.
    response.headers["Cache-Control"] = "public, max-age=9000"
    return response


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
    session = SessionManager.get_active_session(session_id)

    if session is None and os.path.isfile("dev_login.txt"):
        with open("dev_login.txt", "rt") as f:
            print("Using developer auto login: dev_login.txt")
            lines = f.readlines()
            un = lines[0]
            pw = lines[1]
            session_id = SessionManager.create_session(un, load_game=load_game)
            session = SessionManager.get_active_session(session_id)
            response = HTMLResponse("Developer auto login of user: " + un + ". Press refresh to continue.")
            response.set_cookie(key="sessionID", value=session_id)
            # return a simple response, that sets the session cookie.ground_render_list
            return response

    if session is None:
        return templates.TemplateResponse(f'world_view.html', dict(request=request, session=None))

    game_state = session.game_state
    current_map = session.game_state.current_map
    pack_name = game_state.pack.name
    pack = game_state.pack
    # TODO: this loop is needlessly done every frame
    map_lut = {lut.name: {i: pack[slug].idle_animation['class'] if slug is not None else None
                          for i, slug in lut.items()}
               for lut in current_map.luts}

    # work out all the sprites needed to render the ground
    ground_render_list = []
    env_render_list = []
    svp = default_svp_composer

    for step_f in reversed(range(svp.view_dist)):
        fov = svp.fov_table[step_f]
        for step_r in range(-fov, fov+1):
            tile = game_state.get_tile(step_f, step_r, None)
            if tile is not None:
                gnd_idx = tile["ground"]
                gnd_class = map_lut["ground"][gnd_idx]
                if gnd_class is not None:
                    ground_render_list.append((step_f, step_r, gnd_class))

                env_idx = tile["env"]
                env_class = map_lut["env"][env_idx]
                if env_class is not None:
                    a, b, c, d = svp.get_tile_polygon(step_f, step_r)
                    # horizon = (svp.height * svp.horizon_screen_ratio)
                    bottom_pix = (a[1] + c[1]) / 2
                    bottom_per = bottom_pix / svp.height

                    left_pix = (a[0] + b[0]) / 2
                    left_per = left_pix / svp.width

                    # TODO: this is only a simplified scale taken ath the base of the polygon.
                    scale = abs(b[0] - a[0]) / svp.width
                    # print()
                    # print(" bottom_per:", type(bottom_per), bottom_per)
                    # print(" bottom_pix:", type(bottom_pix), bottom_pix)
                    # print(" svp.height: ", type(svp.height), svp.height)

                    env_render_list.append((bottom_per, left_per, scale, env_class))


    context = dict(request=request,
                   pack=pack, pack_name=pack_name,
                   session=session, game_state=game_state,
                   current_map=current_map,
                   map_lut=map_lut,
                   ground_render_list=ground_render_list,
                   env_render_list=env_render_list)

    return templates.TemplateResponse(f'world_view.html', context)

@app.post("/do_action", response_class=ORJSONResponse)
async def do_action(request: Request,
                    session_id: Optional[str] = Cookie(default=None, alias="sessionID")):
    session = SessionManager.get_active_session(session_id)
    if session is None:
        return ORJSONResponse({"message": "not logged in"}, status_code=status.HTTP_404_NOT_FOUND)

    game_state = session.game_state
    data = await request.json()
    action = GameAction[data.get("action").strip().upper()]
    print(f"Received action request: session={session_id}, action={action}")

    game_state.attempt_to_take_action(action)

    return ORJSONResponse({"message": "Move received"})


@app.get("/download/ground_mask/{size_x}/{size_y}/{steps_fwd}/{steps_right}")
@app.get("/download/ground_mask/default/{steps_fwd}/{steps_right}")
async def ground_mask(steps_fwd: int, steps_right: int,
                      view_dist=5, size_x=1280, size_y=720,
                      horizon_screen_ratio=0.5,
                      local_tile_ratio=0.9,
                      bird_eye_vs_worm_eye=0):

    # get file name
    txt_fwd = "BF"[steps_fwd > 0] + str(abs(steps_fwd))
    txt_right = "LR"[steps_right > 0] + str(abs(steps_right))
    xh64 = xxhash.xxh64()
    for q in (horizon_screen_ratio, local_tile_ratio, bird_eye_vs_worm_eye):
        xh64.update(struct.pack("!f", q))
    h = xh64.hexdigest()

    file_name = f"{txt_fwd}_{txt_right}_{h}.webp"
    fmt = f"{size_x}_{size_y}_{view_dist}_sharp"
    path, is_valid = dyna_file_manager.query(["ground_mask", fmt], file_name)

    # is_valid = True
    # regen file
    if not is_valid:
        print("==========================================================\n")
        print(f"=         Regenerating {file_name}\n")
        print("==========================================================\n")
        svp_composer = SingleVanishingPointPainting([], [], size=(size_x, size_y),
                                                    bird_eye_vs_worm_eye=bird_eye_vs_worm_eye, view_dist=view_dist,
                                                    horizon_screen_ratio=horizon_screen_ratio,
                                                    local_tile_ratio=local_tile_ratio)

        img = svp_composer.draw_mask(steps_fwd, steps_right)
        # img.save(path)

        # convert the greyscale image to an alpha channel, because a greyscale
        # image mask does not seem to work on all browsers
        img2 = Image.new("LA", img.size, (255, 255))
        img2.putalpha(img)
        img2.save(path)
        dyna_file_manager.invalidate_cache(["ground_mask", fmt], file_name)

    # done
    return FileResponse(path=path)


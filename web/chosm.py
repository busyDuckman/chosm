import asyncio
import logging
import os
import struct
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Optional

import xxhash

from PIL import Image
from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.responses import RedirectResponse

from game_engine.dynamic_file_manager import DynamicFileManager
from assets.game_constants import AssetTypes
from assets.resource_pack import ResourcePack
from game_engine.game_state import GameState, GameAction
from game_engine.session import session_manager
from game_engine.single_vanishing_point_painting import SingleVanishingPointPainting
from helpers import setup_check

from web.route_user import user_router, set_session_cookie, SESSION_COOKIE
from web.route_pack_management import packs_router
from web.server_data import ServerData
from web.user_db import authenticate


LOG_FILE = os.path.join("logs", "chosm.log")

# Browsers may keep generated / baked files for this long without asking again.
# Baked assets only change on a re-bake, and ground masks only change with the renderer settings.
ASSET_CACHE_SECONDS = 60 * 60
MASK_CACHE_SECONDS = 24 * 60 * 60


def setup_logging():
    """
    Logs go to the console and to logs/chosm.log (rotated at 1MB, keeping 5 old files).
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))

    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(file_handler)
    # uvicorn's loggers do not pass messages up to the root logger, so they need the handler too
    for name in ("uvicorn", "uvicorn.access"):
        logging.getLogger(name).addHandler(file_handler)


setup_logging()
log = logging.getLogger(__name__)

# fastAPI data
app = FastAPI()
app.mount("/web/static", StaticFiles(directory="web/static"), name="static")
app.include_router(user_router)
app.include_router(packs_router)
templates = Jinja2Templates(directory="web/templates")


@app.on_event("startup")
async def startup_event():
    log.info("Starting CHOSM %s, CWD: %s", ServerData.chosm_version, os.getcwd())

    if not setup_check.check_can_serve():
        raise SystemExit(1)

    ServerData.default_svp_composer = SingleVanishingPointPainting([], [], size=(1920, 1024),  # not 1080, see rendering_layout.md
                                                        view_dist=6,
                                                        horizon_screen_ratio=0.5,
                                                        local_tile_ratio=0.9,
                                                        bird_eye_vs_worm_eye=0)

    # load all resource packs
    ServerData.resource_folder = "game_files/baked"
    ServerData.load_resource_packs()

    # setup dynamic file folder, generated files expire when the code base changes
    ServerData.dynamic_folder = "game_files/dynamic_files"
    os.makedirs(ServerData.dynamic_folder, exist_ok=True)
    ServerData.dyna_file_manager = DynamicFileManager(ServerData.dynamic_folder)

    session_manager.game_loader = ServerData.load_game

    # the browser fetches hundreds of sprite files, keep them out of the access log
    class EndpointFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.getMessage().find("GET /download/resource-packs") == -1

    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


@app.get("/")
async def root(request: Request, session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)):
    user_name = None
    if (session := session_manager.get_active_session(session_id)) is not None:
        user_name = session.user_name

    context = dict(version=ServerData.chosm_version,
                   request=request,
                   user_name=user_name)

    return templates.TemplateResponse(request, "landing_page.html", context)


@app.get("/api/resource-management/packs", response_class=ORJSONResponse)
async def manage_packs():
    packs = sorted(list(ServerData.resource_packs.keys()))
    return ORJSONResponse(packs)


@app.get('/api/resource-management/packs/{pack_name}/assets', response_class=ORJSONResponse)
async def manage_assets(pack_name: str, glob: str = None):
    files = ServerData.resource_packs[pack_name].list_assets(glob)
    files = sorted(list(files))
    return ORJSONResponse(files)


@app.get('/api/resource-management/packs/{pack_name}/assets/{asset_name}/files')
async def manage_asset_files(pack_name, asset_name):
    path = ServerData.resource_packs[pack_name].get_asset_path(asset_name)
    files = os.listdir(path)
    return ORJSONResponse(files)


def _asset_file_response(pack_name: str, asset_key, file_name: str) -> Response:
    try:
        file_path = ServerData.resource_packs[pack_name][asset_key].get_file_path(file_name)
    except KeyError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    response = FileResponse(path=file_path)
    response.headers["Cache-Control"] = f"public, max-age={ASSET_CACHE_SECONDS}"
    return response


@app.get("/download/resource-packs/{pack_name}/by_slug/{asset_slug}/{file_name}")
async def get_file(pack_name, asset_slug, file_name):
    return _asset_file_response(pack_name, asset_slug, file_name)


@app.get("/download/resource-packs/{pack_name}/by_type/{asset_type}/by_name/{asset_name}/{file_name}")
async def get_file_by_type(pack_name, asset_type, asset_name, file_name):
    return _asset_file_response(pack_name, (asset_type, asset_name), file_name)


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

    # the folder the sprite's own files are served from
    sprite_css_url = request.url_for('get_file', pack_name=pack_name, asset_slug=asset_slug, file_name='_animation.css')
    sprite_css_path = os.path.split(sprite_css_url.path)[0]

    css_file_path = ServerData.resource_packs[pack_name][asset_slug].get_file_path('_animation.css')
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

    pack = ServerData.resource_packs[pack_name]
    last_pack_modification = pack.get_modification_time()

    # setup where the cached copy will go
    if map_name is None:
        file_name = pack_name + ".css"
        categories = ["pack_css_cache"]
    else:
        file_name = map_name + ".css"
        categories = ["map_css_cache", pack_name]

    # check for ached copy
    path, is_valid = ServerData.dyna_file_manager.query(categories, file_name, expiration_time=last_pack_modification)

    if not is_valid:
        log.info("Regenerating %s", file_name)

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
        ServerData.dyna_file_manager.invalidate_cache(["pack_css_cache"], file_name)

    # done
    response = FileResponse(path=path)
    # calling this valid for 2.5 hours; the hope being that a browser will just see this css include and
    # be happy with what it has.
    response.headers["Cache-Control"] = "public, max-age=9000"
    return response


# ----------------------------------------------------------------------------------------------------------------------
@app.post("/editor/main/{pack_name}")
@app.post("/editor/main/{pack_name}/{asset_slug}")
@app.get("/editor/main/")
@app.get("/editor/main/{pack_name}")
@app.get("/editor/main/{pack_name}/{asset_slug}")
async def editor_view(request: Request, pack_name=None, asset_slug=None, sort_on="name"):
    glob_exp = None
    if request.method == "POST":
        form_data = await request.form()
        glob_exp = form_data["glob-epr"]
        glob_exp = None if len(glob_exp.strip()) == 0 else glob_exp
        log.debug("Editor filter: %s", glob_exp)

    packs = sorted(list(ServerData.resource_packs.keys()))
    pack = None
    resources = {}
    if pack_name is not None:
        pack = ServerData.resource_packs[pack_name]
        resources = pack.get_assets(glob_exp)

    if sort_on == "name":
        # ugly little oneliner: works because dict preserves insertion order
        resources = dict(sorted(resources.items(), key=lambda x: x[1].name))

    context = dict(packs=packs, pack=pack, pack_name=pack_name,
                   glob_exp=glob_exp,
                   resources=resources, asset_slug=asset_slug,
                   request=request)

    return templates.TemplateResponse(request, "editor.html", context)


@app.get("/editor/asset/{pack_name}/{asset_slug}")
async def edit_asset_view(request: Request, pack_name, asset_slug):
    pack = ServerData.resource_packs[pack_name]
    asset_rec = pack[asset_slug]

    context = dict(request=request,
                   pack=pack,
                   pack_name=pack_name,
                   asset_rec=asset_rec,
                   asset_slug=asset_rec.slug)

    return templates.TemplateResponse(request, f'edit_{asset_rec.asset_type_as_string}.html', context)


# ----------------------------------------------------------------------------------------------------------------------
# Game view
# ----------------------------------------------------------------------------------------------------------------------

# css class of each sprite in a map's look up tables, by (pack, map, layer, index). Saves redoing it every frame.
_map_class_luts: Dict[tuple, Dict[str, Dict[int, Optional[str]]]] = {}


def get_map_class_luts(pack: ResourcePack, current_map) -> Dict[str, Dict[int, Optional[str]]]:
    key = (pack.slug, current_map.name)
    if key not in _map_class_luts:
        _map_class_luts[key] = {lut.name: {i: pack[slug].idle_animation['class'] if slug is not None else None
                                           for i, slug in lut.items()}
                                for lut in current_map.luts}
    return _map_class_luts[key]


def build_scene(game_state: GameState) -> dict:
    """
    Works out what the party can see, as the sprites (css classes) to draw and where to draw them.
    """
    pack = game_state.pack
    map_lut = get_map_class_luts(pack, game_state.current_map)
    svp = ServerData.default_svp_composer

    ground_render_list = []
    env_render_list = []
    # paint far to near, so near things are drawn over far things
    for step_f in reversed(range(svp.view_dist)):
        fov = svp.fov_table[step_f]
        for step_r in range(-fov, fov+1):
            tile = game_state.get_tile(step_f, step_r, None)
            if tile is None:
                continue

            gnd_class = map_lut["ground"][tile["ground"]]
            if gnd_class is not None:
                ground_render_list.append((step_f, step_r, gnd_class))

            env_class = map_lut["env"][tile["env"]]
            if env_class is not None:
                b, a, c, d = svp.get_tile_polygon(step_f, step_r)
                bottom_per = max(a[1], b[1], c[1], d[1]) / svp.height
                left_per = min(a[0], b[0]) / svp.width

                # TODO: this is only a simplified scale taken at the base of the polygon.
                scale = svp.get_sprite_scale(step_f) * 1.3
                far_away = step_f >= 3  # distant scenery gets a blue haze
                env_render_list.append((bottom_per, left_per, scale, env_class, far_away))

    # the rows of tiles halve in depth each step, so never quite reach the horizon. The gap is filled
    # with the ground the party is standing on, rather than leaving a dark line.
    here = game_state.get_tile(0, 0, None)
    backdrop_class = map_lut["ground"][here["ground"]] if here is not None else None

    return dict(game_state=game_state,
                pack=pack,
                backdrop_class=backdrop_class,
                ground_render_list=ground_render_list,
                env_render_list=env_render_list)


def all_ground_masks(request: Request) -> List[str]:
    """
    Every ground mask url the view can use, so the browser can fetch them all up front.
    """
    svp = ServerData.default_svp_composer
    return [str(request.url_for('ground_mask', steps_fwd=f, steps_right=r).path)
            for f in range(svp.view_dist)
            for r in range(-svp.fov_table[f], svp.fov_table[f] + 1)]


@app.get("/game/main")
async def game_view(request: Request, session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)):
    session = session_manager.get_active_session(session_id)

    # Developer convenience: dev_login.txt (git ignored) holds a username and password on two lines.
    if session is None and os.path.isfile("dev_login.txt"):
        with open("dev_login.txt", "rt") as f:
            un, pw = [line.strip() for line in f.readlines()[:2]]
        if (user := authenticate(un, pw)) is not None:
            log.info("Using developer auto login: dev_login.txt")
            response = RedirectResponse(request.url_for('game_view').path, status_code=status.HTTP_303_SEE_OTHER)
            set_session_cookie(request, response, session_manager.create_session(user.username))
            return response
        log.warning("dev_login.txt has invalid credentials, ignoring it.")

    if session is None:
        return templates.TemplateResponse(request, 'world_view.html', dict(request=request, session=None))

    context = build_scene(session.game_state)
    context.update(request=request,
                   session=session,
                   pack_name=session.game_state.pack.slug,
                   current_map=session.game_state.current_map,
                   ground_masks=all_ground_masks(request))
    return templates.TemplateResponse(request, 'world_view.html', context)


@app.post("/do_action", response_class=ORJSONResponse)
async def do_action(request: Request,
                    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)):
    """
    Applies a party action, and returns the re-drawn scene for the page to swap in.
    """
    session = session_manager.get_active_session(session_id)
    if session is None:
        return ORJSONResponse({"message": "not logged in"}, status_code=status.HTTP_401_UNAUTHORIZED)

    game_state = session.game_state
    data = await request.json()
    try:
        action = GameAction[str(data.get("action", "")).strip().upper()]
    except KeyError:
        return ORJSONResponse({"message": "unknown action"}, status_code=status.HTTP_400_BAD_REQUEST)

    outcome = game_state.attempt_to_take_action(action)
    log.debug("Action: user=%s, action=%s, ok=%s, pos=%s", session.user_name, action.name, bool(outcome),
              game_state.party.get_pos())

    context = build_scene(game_state)
    context["request"] = request
    scene = templates.get_template("world_scene.html").render(context)
    return ORJSONResponse({"ok": bool(outcome),
                           "message": None if outcome else outcome.why,
                           "map": game_state.current_map.name,
                           "scene": scene})


@app.get("/download/ground_mask/default/{steps_fwd}/{steps_right}")
async def ground_mask(steps_fwd: int, steps_right: int):
    """
    The shape of one ground tile on screen, as an alpha mask (white = tile), for the default view settings.
    """
    svp = ServerData.default_svp_composer

    # get file name
    txt_fwd = "BF"[steps_fwd > 0] + str(abs(steps_fwd))
    txt_right = "LR"[steps_right > 0] + str(abs(steps_right))
    xh64 = xxhash.xxh64()
    for q in (svp.horizon_screen_ratio, svp.local_tile_ratio, svp.bird_eye_vs_worm_eye):
        xh64.update(struct.pack("!f", q))
    h = xh64.hexdigest()

    file_name = f"{txt_fwd}_{txt_right}_{h}.webp"
    fmt = f"{svp.width}_{svp.height}_{svp.view_dist}_sharp"
    path, is_valid = ServerData.dyna_file_manager.query(["ground_mask", fmt], file_name)

    if not is_valid:
        log.info("Regenerating ground mask %s", file_name)
        img = svp.draw_mask(steps_fwd, steps_right)
        if img is None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)

        # convert the greyscale image to an alpha channel, because a greyscale
        # image mask does not seem to work on all browsers
        img2 = Image.new("LA", img.size, (255, 255))
        img2.putalpha(img)
        img2.save(path)
        ServerData.dyna_file_manager.invalidate_cache(["ground_mask", fmt], file_name)

    response = FileResponse(path=path)
    response.headers["Cache-Control"] = f"public, max-age={MASK_CACHE_SECONDS}"
    return response

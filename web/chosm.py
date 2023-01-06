import logging
import os
from typing import List, Dict, NamedTuple

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from chosm.resource_pack import ResourcePack

# fastAPI data

app = FastAPI()
app.mount("/web/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# CHOSM data
resource_folder = ""
resource_packs: Dict[str, ResourcePack] = {}


@app.on_event("startup")
async def startup_event():
    global resource_folder, resource_packs
    print("CWD: " + os.getcwd())

    resource_folder = "game_files/baked"
    assert os.path.exists(resource_folder)

    for d in os.scandir(resource_folder):
        rp = ResourcePack(d.path)
        resource_packs[rp.name] = rp


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/api/resource-management/packs")
def manage_packs():
    global resource_folder, resource_packs

    packs = sorted(list(resource_packs.keys()))
    return packs


@app.get('/api/resource-management/packs/{pack_name}/assets')
def manage_assets(pack_name: str, glob: str = None):
    global resource_folder, resource_packs

    files = resource_packs[pack_name].list_assets(glob)
    files = sorted(list(files))
    return files


@app.get('/api/resource-management/packs/{pack_name}/assets/{asset_name}/files')
def manage_asset_files(pack_name, asset_name):
    global resource_folder, resource_packs

    path = resource_packs[pack_name].get_asset_path(asset_name)
    return os.listdir(path)


@app.get("/download/resource-packs/{pack_name}/{asset_name}/{file_name}")
def get_file(pack_name, asset_name, file_name):
    global resource_folder, resource_packs

    pack = resource_packs[pack_name]
    file_path = pack.get_resource_files(asset_name, file_name, full_path=True)[0]
    return FileResponse(path=file_path)


# ----------------------------------------------------------------------------------------------------------------------
@app.get("/editor/main/")
@app.get("/editor/main/{pack_name}")
@app.get("/editor/main/{pack_name}/{asset_name}")
def editor_view(request: Request, pack_name=None, asset_name=None):
    glob_exp = None
    # glob_exp = session.get("glob_exp", None)
    # if request.method == "POST":
    #     glob_exp = request.form.get("glob-epr")
    #     glob_exp = None if len(glob_exp.strip()) == 0 else glob_exp
    #     session["glob_exp"] = glob_exp if glob_exp is not None else ''
    #     print("Server POST ->", glob_exp)

    # print(pack_name, asset_name)
    packs = sorted(list(resource_packs.keys()))
    pack = None
    resources = {}
    if pack_name is not None:
        pack = resource_packs[pack_name]
        resources = pack.list_assets(glob_exp)

    context = dict(packs=packs, pack=pack, pack_name=pack_name,
                   glob_exp=glob_exp,
                   resources=resources, asset_name=asset_name,
                   request=request)

    return templates.TemplateResponse("editor.html", context)

@app.get("/editor/asset/{pack_name}/{asset_name}")
def edit_asset_view(request: Request, pack_name, asset_name):
    print("edit_asset_view")
    pack = resource_packs[pack_name]
    r_type_token = pack.get_resource_type(asset_name)
    path = pack.get_asset_path(asset_name)
    info = pack.get_info(asset_name)

    context = dict(request=request,
                   pack=pack, pack_name=pack_name,
                   asset_name=asset_name, info=info)

    return templates.TemplateResponse(f'edit_{r_type_token}.html', context)

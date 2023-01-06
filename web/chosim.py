import os
from typing import List, Dict, NamedTuple

from fastapi import FastAPI
from fastapi.responses import FileResponse

from chosm.resource_pack import ResourcePack

app = FastAPI()
resource_folder = ""
resource_packs: Dict[str, ResourcePack] = {}


@app.on_event("startup")
async def startup_event():
    global resource_folder, resource_packs

    resource_folder = "game_files/baked"
    assert os.path.exists(resource_folder)

    for d in os.scandir(resource_folder):
        rp = ResourcePack(d.path)
        resource_packs[rp.name] = rp


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/api/pack-management/resource-packs")
def manage_packs():
    global resource_folder, resource_packs

    packs = sorted(list(resource_packs.keys()))
    return packs


@app.get('/api/asset-management/<pack_name>')
def manage_assets(pack_name: str):
    global resource_folder, resource_packs

    files = resource_packs[pack_name].list_resources()
    files = sorted(list(files))
    return files


@app.get('/api/asset-management/<pack_name>/assets/<asset_name>')
def manage_asset_files(pack_name, asset_name):
    global resource_folder, resource_packs

    path = resource_packs[pack_name].get_resource_path(asset_name)
    return os.listdir(path)


@app.get("/download/resource-packs/<pack_name>/<asset_name>/<file_name>")
def get_file(pack_name, asset_name, file_name):
    global resource_folder, resource_packs

    pack = resource_packs[pack_name]
    file_path = pack.get_resource_files(asset_name, file_name, full_path=True)[0]
    return FileResponse(path=file_path)




# ----------------------------------------------------------------------------------------------------------------------
# @app.route("/editor", defaults = {"pack_name" : None, "resource_name" : None}, methods=['GET', 'POST'])
# @app.route("/editor/<pack_name>", defaults = {"resource_name" : None}, methods=['GET', 'POST'])
# @app.route("/editor/<pack_name>/<resource_name>", methods=['GET', 'POST'])
# def editor_view(pack_name, resource_name):
#     glob_exp = session.get("glob_exp", None)
#     if request.method == "POST":
#         glob_exp = request.form.get("glob-epr")
#         glob_exp = None if len(glob_exp.strip()) == 0 else glob_exp
#         session["glob_exp"] = glob_exp if glob_exp is not None else ''
#         print("Server POST ->", glob_exp)
#
#     # print(pack_name, resource_name)
#     packs = sorted(list(resource_packs.keys()))
#     pack = None
#     resources = {}
#     if pack_name is not None:
#         pack = resource_packs[pack_name]
#         resources = pack.list_resources(glob_exp)
#
#     return render_template('editor.html',
#                            packs=packs,
#                            pack=pack,
#                            glob_exp=glob_exp,
#                            pack_name=pack_name,
#                            resources=resources,
#                            resource_name=resource_name
#                            )

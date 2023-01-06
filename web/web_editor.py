import os
import io
from html import escape
from os.path import split, join
from typing import List, Dict, NamedTuple

from flask import Flask, render_template, send_from_directory, abort, send_file, make_response, redirect, url_for, \
    request, Response, session, render_template_string

from chosm.resource_pack import ResourcePack


SECRET_KEY = os.urandom(32)
resource_packs: Dict[str, ResourcePack] = {}


def init():
    global resource_packs

    for d in os.scandir(app.config['GAME_FILES']):
        rp = ResourcePack(d.path)
        resource_packs[rp.name] = rp


class EditorFlaskApp(Flask):
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        init()
        super(EditorFlaskApp, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)


app = EditorFlaskApp(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['GAME_FILES'] = "game_files/baked"
# app.use_x_sendfile = True

app.run()

@app.route("/")
def landing():
    return render_template_string("""
    <!doctype html>
    <html>
        <body>
            <a href="{{ url_for('editor_view') }}">Editor</a>
            <a href="{{ url_for('editor_view') }}">World</a>
        </body>
    </html>
    """)
    # return html. url_for("editor_view")

@app.route("/editor", defaults = {"pack_name" : None, "resource_name" : None}, methods=['GET', 'POST'])
@app.route("/editor/<pack_name>", defaults = {"resource_name" : None}, methods=['GET', 'POST'])
@app.route("/editor/<pack_name>/<resource_name>", methods=['GET', 'POST'])
def editor_view(pack_name, resource_name):
    glob_exp = session.get("glob_exp", None)
    if request.method == "POST":
        glob_exp = request.form.get("glob-epr")
        glob_exp = None if len(glob_exp.strip()) == 0 else glob_exp
        session["glob_exp"] = glob_exp if glob_exp is not None else ''
        print("Server POST ->", glob_exp)

    # print(pack_name, resource_name)
    packs = sorted(list(resource_packs.keys()))
    pack = None
    resources = {}
    if pack_name is not None:
        pack = resource_packs[pack_name]
        resources = pack.list_resources(glob_exp)

    return render_template('editor.html',
                           packs=packs,
                           pack=pack,
                           glob_exp=glob_exp,
                           pack_name=pack_name,
                           resources=resources,
                           resource_name=resource_name
                           )

@app.route("/edit_resource/<pack_name>/<resource_name>", methods=['GET', 'POST'])
def edit_resource(pack_name, resource_name):
    pack = resource_packs[pack_name]
    r_type_token = pack.get_resource_type(resource_name)
    path = pack.get_resource_path(resource_name)
    info = pack.get_info(resource_name)

    return render_template(f'edit_{r_type_token}.html',
                           pack=pack,
                           pack_name=pack_name,
                           resource_name=resource_name,
                           info=info
                           )


@app.route("/download/<pack_name>/<resource_name>/<file_name>")
def get_file(pack_name, resource_name, file_name):
    pack = resource_packs[pack_name]
    path = pack.get_resource_files(resource_name, file_name, full_path=True)[0]
    # at this point path could be anywhere, even a different (masking/chained) resource pack.

    # get file to play nicely with send_from_directory(..)
    path = os.path.relpath(path, app.config['GAME_FILES'])
    # print(path)
    # TODO get web server to send file
    return send_from_directory("../game_files/baked", path)


@app.route("/packs")
def list_resource_packs():
    packs = sorted(list(resource_packs.keys()))
    return packs


@app.route('/packs/<pack_name>')
def list_resources(pack_name: str):
    files = resource_packs[pack_name].list_resources()
    files = sorted(list(files))
    return files


@app.route('/packs/<pack_name>/resources_by_name/<file_name>')
def list_files(pack_name, file_name):
    path = resource_packs[pack_name].load_resource_as_mam_file(file_name)
    return os.listdir(path)





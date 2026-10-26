# CHOSM tasks, run `just` to list them.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    @just --list

# Install python and all dependencies into .venv, and offer to create a test user account
setup:
    uv sync
    uv run python -m web.user_db

# Bake game assets from ./game_files/dos/ and ./game_files/chosm_art/ into ./game_files/baked/
bake: _bake-game-files
    uv run python -m game_files.chosm_art.bake

# cc_file.py uses paths relative to mam_game/, and imports from the project root.
[working-directory: 'mam_game']
_bake-game-files $PYTHONPATH=justfile_directory():
    uv run python cc_file.py

# Run the web server with auto reload, at http://127.0.0.1:8000
serve:
    uv run python -m helpers.setup_check
    uv run uvicorn web.chosm:app --reload

# Run the tests
test *args:
    uv run pytest {{args}}

# Upgrade locked dependency versions
upgrade:
    uv lock --upgrade

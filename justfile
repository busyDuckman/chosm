# CHOSM tasks, run `just` to list them.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    @just --list

# Install python and all dependencies into .venv, and offer to create a test user account
setup:
    uv sync
    uv run python -m web.user_db

# cc_file.py uses paths relative to mam_game/, and imports from the project root.
[doc('Bake game assets from the .cc files in ./game_files/dos/ into ./game_files/baked/')]
[working-directory: 'mam_game']
bake $PYTHONPATH=justfile_directory():
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

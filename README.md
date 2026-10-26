# CHOSM

[![Project Status: Inactive](https://www.repostatus.org/badges/latest/inactive.svg)](https://www.repostatus.org/#inactive)
[![License: MIT](https://img.shields.io/github/license/busyDuckman/chosm)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![uv](https://img.shields.io/badge/uv-managed-de5fe9?logo=uv)](https://docs.astral.sh/uv/)

> [!NOTE]
> I worked on this project in 2022 and got to about TRL 3.
> I learnt a few things I wanted to (mostly about web development etc) 
> and then decided the juice was not worth the squeeze going forward.
> So I am mothballing it. 


# Mothballing tasks performed:
  - adopt uv over pip
  - added a justfile
  - security audit, updated the login / session handling
  - launch and fix any major issues
    - moves update the scene in place rather than reloading the page.
    - textures are cached by the browser
    - logging goes to logs/chosm.log


# Salvageable work:
  - Python port of the Xeen loaders:
    - See my other xeen repo [OpenXeen](https://github.com/busyDuckman/OpenXeen)
    - This holds a python adaption of the Xeen CC file loaders, which is a great leg up 
      for anyone wanting to work in that area.
  - The vanishing-point renderer in [game_engine/single_vanishing_point_painting.py](game_engine/single_vanishing_point_painting.py).
    It's the actual research idea behind the project, and its view height and perspective 
    code advances on what was normal for the 80's/90's.
  - The dice notation parser in [game_engine/dice.py](game_engine/dice.py) is very handy
  - [observable_dict.py](helpers/observable_dict.py) and [linkable_dict.py](helpers/linkable_dict.py)
    are useful little ADTs for change notification and mergeable dictionaries. They also have unit tests.

## Screenshots

| Menu |
|:---:|
| [![Menu](docs/screenshots/menu_resized.jpg)](docs/screenshots/menu.jpg) |

| Editor | Game |
|:---:|:---:|
| [![Editor](docs/screenshots/editor_resized.jpg)](docs/screenshots/editor.jpg) | [![Game](docs/screenshots/game_resized.jpg)](docs/screenshots/game.jpg) |


# About 
This is an experimental project to explore what a modern version of a particular
type of game engine would look like. 

The type of engine was used in Might and Magic (MaM), Eye of the beholder (EoB), 
and Lands of Lore (LoL). It used a centered vanishing point to direct a sprite 
based painting algorithm. The world view was presented above the portraits of a 
group of adventurers. 

I could find no industry term for this type of rendering, so I am calling it 
a "Centred Horizon Ordered Sprite Montage" (CHOSM).

The aim was to present the results in a web-browser based MMORPG.

For research into the rendering method, this project bootstraps itself from the data files
of the "Might and Magic" series of video games. **No game data files are included in this repository.**
To run the server you need your own copy of Might and Magic: Darkside of Xeen; copy its
DARK.CC and DARK.CUR files into ./game_files/dos/


## Running the code

Requirements:
  - [uv](https://docs.astral.sh/uv/), which installs the right Python version and all packages.
  - [just](https://github.com/casey/just) (optional), a command runner for the tasks below.

Setup:

    just setup                # uv sync, then offers to create a test user account

Baking the game assets (extracts the sprites, maps etc from the cc files, and bakes
the replacement art in game_files/chosm_art):

    # Before doing this, first copy DARK.CC and DARK.CUR into ./game_files/dos/
    just bake

Running the web server:

    just serve   # (uv run uvicorn web.chosm:app --reload)

    # Landing page
    http://127.0.0.1:8000    

    # The game (arrow keys or WASD to move and turn)
    http://127.0.0.1:8000/game/main

    # Editor is at
    http://127.0.0.1:8000/editor/main

    # API testing and doco
    http://127.0.0.1:8000/docs


**NOTE:** If you saved the test account to dev_login.txt during `just setup`, opening the game
page logs you in automatically.

Running the tests:

    just test

## Code doco

The code and software structure is documented, see: 
[docs/code_structure.md](docs/code_structure.md)


## Disclaimer
The aim of this project is to investigate ideas, **not** recreate, or provide
access to the Might and Magic Games. If you wish to play these games, this can be
done via:
  - GOG: https://www.gog.com/en/game/might_and_magic_6_limited_edition
  - Ebay: search for original media
  - Dosbox: https://www.dosbox.com/
  - ScummVM: https://wiki.scummvm.org/index.php/Might_and_Magic:_World_of_Xeen


## References & Acknowledgments:
  - Might and Magic reverse Engineering:
    - https://xeen.fandom.com/wiki/Xeen_Wiki
      - David Goldsmith
      - Mat Taylor
  - fastAPI (This was my first fast API proj, and I think it's awesome)
  - Cool parchment idea: https://codepen.io/AgnusDei/pen/NWPbOxL


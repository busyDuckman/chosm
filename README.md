# CHOSM

**This project is in very early development, and is not yet ready for general use.**
I am publishing it as some people may want a python port of [OpenXeen](https://github.com/busyDuckman/OpenXeen)

This is an experimental project to explore what a modern version of a particular
type of game engine would look like. 

The type of engine was used in Might and Magic (MaM), Eye of the beholder (EoB), 
and Lands of Lore (LoL). It used a centered vanishing point to direct a sprite 
based painting algorith. The world view was presented above the portraits of a 
group of adventurers. 

I could find no industry term for this type of rendering, so I am calling it 
a "Centred Horizon Ordered Sprite Montage" (CHOSM).

This project aims to present its results in a web-browser based MMORPG.

For research purposes and commentary on the methods, this project currently bootstraps
itself with data from "Might and Magic" series of video games. IANAL, but I believe this 
constitutes fair use. The bootstrap data is not in this repository, you need
to source that material yourself to run the server. To do this copy the
".cc" files from MaM4-5 into ./game_files/dos/

## Running the code

Requirements:
  - Python 3.10 or higher, with all the trimmings.


Setup requirements for linux systems: 


    sudo apt install python3.10  
    sudo apt-get install python3.10-distutils
    python3.10 -m pip install --upgrade pip
    sudo apt-get install python3.10-dev    

Setup python packages:

    pip install requirements.txt

Extracting data from cc files:
    
    # copy game files into ./game_files/dos/
    cd mam_game
    python cc_file.py

Running the web server:

    python -m uvicorn web.chosm:app --reload

    # Landing page
    http://127.0.0.1:8000    

    # Editor is at
    http://127.0.0.1:8000/editor/main

    # API testing and doco
    http://127.0.0.1:8000/docs

## Concepts being explored
The scope of this project is ambitious, I believe this type of engine offers
some very interesting prospects; I am putting this vision into a separate file
and will add it here shortly.

## Disclaimer
The aim of this project is to investigate ideas, **not** recreate, or provide
access to the Might and Magic Games. If you wish to play these games, this can be
done via:
  - COG: https://www.gog.com/en/game/might_and_magic_6_limited_edition
  - Ebay: search for original media
  - Dosbox: https://www.dosbox.com/
  - ScummVM: https://wiki.scummvm.org/index.php/Might_and_Magic:_World_of_Xeen


## References & Acknowledgments:
Might and Magic reverse Engineering:
  - https://xeen.fandom.com/wiki/Xeen_Wiki
    - David Goldsmith
    - Mat Taylor

fastAPI

Cool parchment idea:
  - https://codepen.io/AgnusDei/pen/NWPbOxL





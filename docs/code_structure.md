# Software Overview

| **Software Area**   | **Actions**                                        | **Code**    | **Notes**                                    |
|---------------------|----------------------------------------------------|-------------|----------------------------------------------|
|          Web Server | Edit resources and play game                       | /web        | Currently flask based, will move to fastAPI. |
|         Game Engine | Interaction, Maps, Player, AI, Game state, Scripts | /game_engine |                                              |
| Resource Management | index and maintain resources                       | /chosm      |                                              |
| Might & Magic       | Transform M&M files to resources                   | /mam_game   | Other game importers would be possible.      |

## Web Server
Todo:
  - Get basic game view render
  - containerise a web stack (https://hub.docker.com/r/tiangolo/uvicorn-gunicorn-fastapi)
  - create a devops pipeline git -> docker -> droplet
  - stream resource files to browser direct via webserver, not the API  

## Game Engine
Todo:
  - Get a running game loop and session manager.
  - Scripting engine

This will be a time-consuming thing to complete and is low priority at the moment. 

## Resource Management
Todo:
  - "edit_packs", zip asset files the user can edit on their local machine, then re-upload.  

**Chosm uses "Resource Packs" to hold "assets" used to create "Worlds" in the game.** 

One world can use multiple resource packs, and a resource packs can be used in many worlds.

Features:
  - TODO: Resource packs are versioned, and games can use a version pinned as a "release".
  - Resource packs can "overload" other resource packs, replacing game assets for a world.
  - Resource packs can "link" to other resource packs, allowing worlds to use resources 
    from other packs. 

### Assets
Assets represent an item, object, entity, script, NPC, sprite, etc used to create a world.
Assets must be of a specific type, limited to:
  - Sprite
  - Map
  - NPC
  - NPC database
  - Palette
  - Text file
  - Binary file
  - Sound fx
  - Music
  - (more to come, including scripting)
  - Note: there are no "image" resources, everything is a sprite.

The game server only loads asset metadata, to compose the html that will render a scene.
It then sends the html to the client which will then retrieve the required resource files 
from the server to render the scene.

#### Assets have both an ID and a NAME. 
A name must be present and is paired with the type to create a unique "slug"
(primary means to identify an asset).


ID's (integer) are only optional metadata, They don't need to be unique.
The ID's help support running legacy games; and enable certain game logic 
(eg: spite 37, works with sound 37; or the ground texture ID's match the 
tile number in a map.)

## files and naming conventions
An asset is (typically) stored in a folder with the same name as the slug.
This folder contains multiple files concerning the resource.

Every asset has a "info.json" which defines what the game server needs to
know about the asset. Eg:
  - The size of the sprite, so that it can be properly positioned in the html output.
  - The duration of a sound effect.

Files in the folder starting with a "_"  (eg: "_frame_0021.pmg") are considered 
"secondary files". The others are primary files. Secondary files are generated
by the resource manager from the primary files. They can be safely deleted if 
modifying game content.


#### Slugs and retrieving assets, by example.
A sprite "ice-dragon-027" will get the slug "sprite-ice-dragon-027".
A type name can not have a '-', so parsing the slug is easy.

An "AssetRecord" for the ice dragon sprite can now
be accessed via:

    # via keys
    resource_pack["sprite-ice-dragon-027"]
    resource_pack[AssetTypes.SPRITE, "ice-dragon-027"]    

    # or more verbosly
    resource_pack.get_asset_by_slug("sprite-ice-dragon-027")
    resource_pack.get_asset_by_name(AssetTypes.SPRITE, "ice-dragon-027")

    # or from a resource dictionary
    resource_pack.get_assets_by_type(AssetTypes.SPRITE)["ice-dragon-027"]
    resource_pack.get_sprites()["ice-dragon-027"]


Files for the sprite can be accessed via:

    slug = resource_pack[Sprite, "ice-dragon-027"].slug
    resource_pack.get_resource_files(slug, "*.*", full_path=True)
    
    # to get metadata from the info.json
    width = resource_pack[Sprite, "ice-dragon-027"]["width"]

    # or just get the folder
    resource_pack[Sprite, "ice-dragon-027"]["path"]

### There are two classes that should be understood regarding CHOSM assets: 

AssetRecord:
  - built for use by the web server
  - store metadata for the viewer and editor
  - store a slug representing the folder
  - stack to override each other
  - validate their own structure
  - can bootstrap an Asset from primary files

Asset:
  - built for use by software creating graphics for the game.
    - Might and magic asset import scripts
    - Sprite resize & creation AI
  - can be created from in memory objects
  - holds raw data, such as images and sound in memory
  - can perform operations on the data
  - can "bake" that data to an asset.
    - by this process, it will create secondary files from primary files

## Might & Magic
Todo:
  - Catalog sprites
  - Load Event scripts
  - Sound FX
  - Music
  - MaM 3 support
  - MaM 1&2 support

This concerns extracting game data and "baking" it to the resource file format.  
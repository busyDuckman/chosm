
Some notes on creating graphics etc.

# Sprite montage view 
Every image is a sprite, if you don't want it animated just use one frame.

The view is rendered as a single sky image above a composition of ground images.
Ground images are a set of sprites that each represent what the ground looks like 
if that was the only surface visible.

The Chosm engine creates masks to blend these images together using a configurable central 
vanishing point projection.

In the world of modern 3d graphics this may sound silly; but the advantages are easily overlooked:
  - There is no ugly repetition of ground textures (which plague 3d systems).
  - The images required are simple to generate, and don't need to tessellate.
     - You can go strait from a proto fo a flat landscape for both sky/ground (it works really well).
     - Stable diffusion is happy to create this type of image (include "flat horizon" in the prompt)
     - You can paint this type of image, just keep a flat horizon and Bob(Ross)'s your uncle.
  - You can artistically work the ground against your sky, painting in any specific highlights you wish.
 
The screen is specified in %, and scaled to whatever window confronts the browser.
The horizon is positioned at 50% in the usual case, though that can and will change.
Graphics are stretched a little in rendering, which is considered a fair compromise.

Ideally the ground and sky textures are 1920 by 512. This odd resolution is to
allow current AI art workflows to use convenient 64 pixel increments.


# Map / Environment

The map is grid based and information is stored as layers. Layer information can be integer, float, string or boolean.

There are five default layers that the scene render understands. Any other layers are for scripting etc.
The chosm engine compresses a layers well if it is sparse (mostly populated by the same value).

The default layers are:
  -   "height": The elevation of the land at this point.
  -   "ground": An index into a list of ground images
  -  "surface": A surface on top of the ground (ie rendered as a second pass over the ground)
  -     "wall": A wall
  -    "decal": Something rendered on top of the wall
  -      "env": Trees / rocks / etc.
  - "building": A hut, wagon, tent, cave entrance etc.

Associate sprites with the layers (except for height) by adding a AssetLut with the same name.
or add "-map" for the timed map sprite look up.

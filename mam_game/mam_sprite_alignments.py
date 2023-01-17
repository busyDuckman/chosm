from PIL import Image
import helpers.pil_image_helpers as pih
from chosm.sprite_asset import sprite_from_baked_folder, SpriteAsset, AnimLoop

def get_draw_structs():
    # source https://xeen.fandom.com/wiki/MAZExxxx.DAT_File_Format
    # I edited it slightly
    outdoor_surface = """
    0x0000  18    8	67	0	0x0000	Surface tile 4 steps forward, 3 left
    0x0000	19	38	67	0	0x0000	Surface tile 4 steps forward, 2 left
    0x0000	20	84	67	0	0x0000	Surface tile 4 steps forward, 1 left
    0x0000	21	103	67	0	0x0000	Surface tile directly 4 steps forward
    0x0000	22	117	67	0	0x0000	Surface tile 4 steps forward, 1 right
    0x0000	23	117	67	0	0x0000	Surface tile 4 steps forward, 2 right
    0x0000	24	134	67	0	0x0000	Surface tile 4 steps forward, 3 right
    
    0x0000	11	8	73	0	0x0000	Surface tile 3 steps forward, 3 left
    0x0000	12	8	73	0	0x0000	Surface tile 3 steps forward, 2 left
    0x0000	13	30	73	0	0x0000	Surface tile 3 steps forward, 1 left
    0x0000	14	87	73	0	0x0000	Surface tile directly 3 steps forward
    0x0000	15	129	73	0	0x0000	Surface tile 3 steps forward, 1 right
    0x0000	16	154	73	0	0x0000	Surface tile 3 steps forward, 2 right
    0x0000	17	181	73	0	0x0000	Surface tile 3 steps forward, 3 right
    
    0x0000	6	8	81	0	0x0000	Surface tile 2 steps forward, 2 left
    0x0000	7	8	81	0	0x0000	Surface tile 2 steps forward, 1 left
    0x0000	8	63	81	0	0x0000	Surface tile directly 2 steps forward
    0x0000	9  145	81	0	0x0000	Surface tile 2 steps forward, 1 right
    0x0000	10	202	81	0	0x0000	Surface tile 2 steps forward, 2 right
    
    0x0000	3	8	93	0	0x0000	Surface tile 1 step forward, 1 left
    0x0000	4	31	93	0	0x0000	Surface tile directly 1 step forward
    0x0000	5	169	93	0	0x0000	Surface tile 1 step forward, 1 right
    
    0x0000	0	8	109	0	0x0000	Surface tile directly 1 step left
    0x0000	1	8	109	0	0x0000	Surface tile player is currently on
    0x0000	2	201	109	0	0x0000	Surface tile directly 1 step right
    """

    outdoor_surface = [q.strip().split(maxsplit=6) for q in outdoor_surface.splitlines()]
    outdoor_surface = [q for q in outdoor_surface if len(q) > 0]

    outdoor_surface = {int(frame): (int(x)-8, int(y)-67) for i, (_, frame, x, y, scale, flags, desc)
                       in enumerate(outdoor_surface)}

    return outdoor_surface



def simplify_ground_sprite(gnd: SpriteAsset):
    """
    Creates a new sprite where all frames are 216, 73; and all ground segments
    :return:
    """
    outdoor_surface_pos_lut = get_draw_structs()
    images = []
    for i, frame in enumerate(gnd.frames):
        img = Image.new(mode="RGBA", size=(216, 73))
        x, y = outdoor_surface_pos_lut[i]
        img.paste(frame, (x, y), mask=frame)
        images.append(img)

    return images


def flatten_ground_sprite(gnd: SpriteAsset, new_name=None) -> SpriteAsset:
    outdoor_surface_pos_lut = get_draw_structs()
    img = Image.new(mode="RGBA", size=(216, 73))
    for i, frame in enumerate(gnd.frames):
        x, y = outdoor_surface_pos_lut[i]
        # frame2 = pih.hue_rotate(frame, i * 30)
        img.paste(frame, (x, y), mask=frame)

    if new_name is None:
        new_name = gnd.name + "_flat"
    return gnd.copy(new_name, frames=[img], animations=[AnimLoop.make_static(0)])


def flatten_sky_sprite(sky: SpriteAsset, new_name=None) -> SpriteAsset:
    cropped_frames = []
    for frame in sky.frames:
        bounds = pih.image_bounds_transparent_background(frame)
        frame_2 = frame.crop(bounds)
        cropped_frames.append(frame_2)

    img = pih.stack_images(cropped_frames)
    if new_name is None:
        new_name = sky.name + "_flat"
    return sky.copy(new_name, frames=[img], animations=[AnimLoop.make_static(0)])


def main():
    gnd = sprite_from_baked_folder("../game_files/baked/dark-cccur-darkside-pc-dos/sprite-desert-srf")
    gnd_flat = flatten_ground_sprite(gnd)
    imgs = simplify_ground_sprite(gnd)
    # gnd_flat.frames[0].show("composite ground image")

    sky = sprite_from_baked_folder("../game_files/baked/dark-cccur-darkside-pc-dos/sprite-sky-sky")


if __name__ == '__main__':
    main()

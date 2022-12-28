from PIL import Image, ImageOps, ImageFont, ImageDraw
import numpy as np


def image_bounds_black_background(img: Image.Image):
    np_img = np.array(img)
    mask = np.max(np_img, axis=2) > 0
    return _image_bounds_mask(mask)


def image_bounds_transparent_background(img: Image.Image):
    mask = np.array(img.convert('RGBA').split()[-1])
    return _image_bounds_mask(mask)


def _image_bounds_mask(mask):
    bounds = []
    for ax in range(2):
        ax_mask = np.max(mask, axis=ax)
        cs = np.cumsum(ax_mask)
        bounds.append(max(np.argwhere(cs == cs[0]))[0])
        bounds.append(min(np.argwhere(cs == cs[-1]))[0] + 1)  # +1 because of how cumsum works
    x1, x2, y1, y2 = bounds
    return x1, y1, x2, y2


def pad_image_to_make_square(img: Image.Image, fill=None, return_box=False) -> Image.Image:
    w, h = img.size
    if w == h:
        if return_box:
            return img.copy(), (0, 0, w, h)
        else:
            return img.copy()
    else:
        # image is centered, by half the w vs h difference.
        offset = abs(w - h) // 2
        pos = (0, offset) if w > h else (offset, 0)

        s = max(w, h)
        if fill is None:
            depth = len(img.getpixel((0, 0)))
            fill = tuple([0 for _ in range(depth)])

        img2 = Image.new(img.mode, (s, s), fill)
        img2.paste(img, pos)
        if return_box:
            return img2, (pos[0], pos[1], w, h)
        else:
            return img2


def resize_keep_aspect(img, max_dim) -> Image.Image:
    """
    Resize image, keeping aspect ratio.
    :param img:
    :param max_dim: the new size of the greater of (width, height)
    :return:
    """
    if type(img) is list:
        return [resize_keep_aspect(q, max_dim) for q in img]

    if img.width > img.height:
        w = max_dim
        h = int(img.height * (max_dim / img.width))
    else:
        h = max_dim
        w = int(img.width * (max_dim / img.height))
    img2 = img.resize((w, h))
    return img2


def thumb_nail(img, h=128) -> Image.Image:
    if type(img) is np.ndarray:
        img = Image.fromarray(img)

    w = img.width * (h / img.height)
    return img.resize((int(w), h))


def join_images(images, mode=None, bg_col=[0, 0, 0]) -> Image.Image:
    return _append_images(images, mode, [1, 0], bg_col)


def stack_images(images, mode=None, bg_col=[0, 0, 0]) -> Image.Image:
    return _append_images(images, mode, [0, 1], bg_col)


def _append_images(images, mode, direction, bg_col) -> Image.Image:
    direction = np.array(direction)

    widths, heights = zip(*(i.size for i in images))
    if direction[0]:
        height = max(heights)
        width = sum(widths)
    else:
        height = sum(heights)
        width = max(widths)

    mode = images[0].mode if mode is None else mode
    if bg_col is not None:
        new_im = Image.new(mode, (width, height), tuple(bg_col))
    else:
        new_im = Image.new(mode, (width, height))

    offset = np.array([0, 0])
    for im in images:
        if 'a' in im.mode.lower():
            new_im.paste(im, tuple(offset), im)
        else:
            new_im.paste(im, tuple(offset))

        offset += (im.size * direction)

    return new_im


def annotate(image: Image.Image,
             top_text: str, top_text_size=16,
             bottom_text: str = None, bottom_text_size=12,
             font_name: str = "LiberationSans-Regular.ttf"):
    img = image.copy()  # dont draw on the original, return a copy
    draw = ImageDraw.Draw(img, "RGBA")

    x_off = min(img.width // 20, 16)

    if top_text is not None and len(top_text.strip()) > 0:
        font = ImageFont.truetype(font_name, top_text_size)
        box = draw.textbbox((0, 0), top_text, font=font)
        draw.rectangle([(0, 0), (img.width, box[3] + 3)], fill="#60606060")
        draw.text((x_off, 0), top_text, (255, 255, 255), font=font)

    if bottom_text is not None and len(bottom_text.strip()) > 0:
        font = ImageFont.truetype(font_name, bottom_text_size)
        box = draw.textbbox((0, 0), bottom_text, font=font)
        h = box[3] + 4
        draw.rectangle([(0, img.height - h), (img.width, img.height)], fill="#60606060")
        draw.text((x_off, img.height - h + 1), bottom_text, (240, 255, 16), font=font)

    return img
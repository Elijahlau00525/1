import base64
import io

from PIL import Image


def _strip_data_url_prefix(data: str) -> str:
    if "," in data and data.lower().startswith("data:image"):
        return data.split(",", 1)[1]
    return data


def decode_base64_image(image_base64: str) -> Image.Image:
    raw = base64.b64decode(_strip_data_url_prefix(image_base64))
    image = Image.open(io.BytesIO(raw)).convert("RGBA")
    return image


def dominant_color_from_base64(image_base64: str) -> tuple[str, float, float, float]:
    image = decode_base64_image(image_base64)
    tiny = image.resize((48, 48))
    pixels = list(tiny.getdata())

    valid = [(r, g, b) for (r, g, b, a) in pixels if a > 24]
    if not valid:
        valid = [(160, 160, 160)]

    red = round(sum(p[0] for p in valid) / len(valid))
    green = round(sum(p[1] for p in valid) / len(valid))
    blue = round(sum(p[2] for p in valid) / len(valid))

    hue, sat, lig = rgb_to_hsl(red, green, blue)
    hex_color = f"#{red:02x}{green:02x}{blue:02x}"
    return hex_color, hue, sat, lig


def suggest_clothing_metadata(image_base64: str) -> tuple[str, str, list[str]]:
    image = decode_base64_image(image_base64)
    width, height = image.size
    ratio = width / max(height, 1)

    alpha = image.split()[-1]
    bbox = alpha.getbbox()
    coverage = 0.0
    if bbox:
        box_w = max(1, bbox[2] - bbox[0])
        box_h = max(1, bbox[3] - bbox[1])
        coverage = (box_w * box_h) / max(width * height, 1)

    _, hue, sat, lig = dominant_color_from_base64(image_base64)

    if coverage < 0.2:
        category = "accessory"
    elif ratio > 1.35:
        category = "shoes"
    elif ratio < 0.58:
        category = "outer"
    else:
        category = "top"

    if ratio > 0.95:
        fit = "loose"
    elif ratio < 0.65:
        fit = "slim"
    else:
        fit = "regular"

    tags: list[str] = []
    if sat < 20:
        tags.append("neutral")
    if 25 <= lig <= 75 and sat <= 45:
        tags.append("clean")
    if sat > 55:
        tags.append("accent")
    if 35 <= hue <= 170:
        tags.append("fresh")
    if hue >= 320 or hue <= 20:
        tags.append("warm")

    return category, fit, tags


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    rn = r / 255
    gn = g / 255
    bn = b / 255

    max_c = max(rn, gn, bn)
    min_c = min(rn, gn, bn)
    delta = max_c - min_c

    light = (max_c + min_c) / 2
    sat = 0.0
    hue = 0.0

    if delta != 0:
        sat = delta / (1 - abs(2 * light - 1))

        if max_c == rn:
            hue = 60 * (((gn - bn) / delta) % 6)
        elif max_c == gn:
            hue = 60 * (((bn - rn) / delta) + 2)
        else:
            hue = 60 * (((rn - gn) / delta) + 4)

    return round(hue, 2), round(sat * 100, 2), round(light * 100, 2)

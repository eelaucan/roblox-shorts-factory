"""Render a Roblox-style chat bubble (white fill, thick black outline, tail) as RGBA."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont


@dataclass
class BubbleStyle:
    font: str
    font_size: int
    text_color: tuple[int, int, int]
    bubble_color: tuple[int, int, int]
    outline_color: tuple[int, int, int]
    outline_width: int
    corner_radius: int
    padding: tuple[int, int]
    max_width_px: int


@lru_cache(maxsize=8)
def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # Fallback so the pipeline still runs before a font is dropped in.
        return ImageFont.load_default(size=size)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_text_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if font.getlength(trial) <= max_text_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_bubble(text: str, speaker: str, style: BubbleStyle,
                  side: str = "left") -> Image.Image:
    font = _load_font(style.font, style.font_size)
    name_font = _load_font(style.font, max(18, int(style.font_size * 0.5)))
    pad_x, pad_y = style.padding
    ow = style.outline_width

    max_text_w = style.max_width_px - 2 * (pad_x + ow)
    lines = _wrap(text, font, max_text_w)

    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    text_w = max((font.getlength(ln) for ln in lines), default=1)
    text_h = line_h * len(lines)

    name_h = name_font.getmetrics()[0] + name_font.getmetrics()[1] + 6
    tail = int(style.font_size * 0.55)

    box_w = int(text_w + 2 * pad_x)
    box_h = int(text_h + 2 * pad_y)
    img_w = box_w + 2 * ow
    img_h = box_h + 2 * ow + name_h + tail

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    box_top = name_h
    box = (ow, box_top + ow, ow + box_w, box_top + ow + box_h)

    # speaker name tag above the bubble
    name_x = box[0] if side == "left" else box[2] - name_font.getlength(speaker)
    d.text((name_x, 0), speaker, font=name_font, fill=style.bubble_color,
           stroke_width=max(2, ow // 2), stroke_fill=style.outline_color)

    # rounded rect with outline
    d.rounded_rectangle(box, radius=style.corner_radius, fill=style.bubble_color,
                        outline=style.outline_color, width=ow)

    # tail — a little triangle hanging off the bottom, toward the speaker's side
    tx = box[0] + box_w * (0.22 if side == "left" else 0.78)
    ty = box[3]
    d.polygon([(tx - tail * 0.6, ty - 2), (tx + tail * 0.6, ty - 2), (tx, ty + tail)],
              fill=style.bubble_color, outline=style.outline_color)
    # cover the seam left by the triangle outline sitting on the box border
    d.line([(tx - tail * 0.6 + ow, ty - 2), (tx + tail * 0.6 - ow, ty - 2)],
           fill=style.bubble_color, width=ow)

    # text
    ty0 = box[1] + pad_y
    for i, ln in enumerate(lines):
        lx = box[0] + pad_x
        if side == "right":
            lx = box[2] - pad_x - font.getlength(ln)
        d.text((lx, ty0 + i * line_h), ln, font=font, fill=style.text_color)

    return img

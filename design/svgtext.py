"""Shape text with HarfBuzz and emit outlined SVG paths.

GitHub's image proxy blocks web fonts, so every glyph in the generated SVGs is
converted to a <path>. Fonts live in design/fonts/ and are not committed
(see design/build.py for where to download them).
"""

from __future__ import annotations

from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONTS = {
    "serif": FONT_DIR / "Fraunces.ttf",
    "serif-italic": FONT_DIR / "FrauncesItalic.ttf",
    "mono": FONT_DIR / "Mono.ttf",
    "brush": FONT_DIR / "MaShanZheng.ttf",
    "sc": FONT_DIR / "NotoSerifSC.ttf",
}
_cache: dict = {}


def _font(key: str, axes: dict):
    k = (key, tuple(sorted(axes.items())))
    if k not in _cache:
        face = hb.Face(hb.Blob.from_file_path(str(FONTS[key])))
        font = hb.Font(face)
        if axes:
            font.set_variations(axes)
        _cache[k] = (font, face.upem)
    return _cache[k]


def _is_cjk(ch: str) -> bool:
    return ord(ch) > 0x2E7F


def _runs(text: str, key: str, cjk: str):
    """Split text into runs; CJK characters go to the `cjk` font."""
    out: list[list] = []
    for ch in text:
        k = cjk if (_is_cjk(ch) and key not in ("brush", "sc")) else key
        if out and out[-1][0] == k:
            out[-1][1] += ch
        else:
            out.append([k, ch])
    return out


def _layout(text, size, key, axes, tracking, cjk):
    glyphs, x = [], 0.0
    for k, chunk in _runs(text, key, cjk):
        if k == key:
            ax = axes
        elif k == "sc":
            ax = {"wght": axes.get("wght", 400)}
        else:
            ax = {}
        font, upem = _font(k, ax)
        buf = hb.Buffer()
        buf.add_str(chunk)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"kern": True, "liga": True})
        scale = size / upem
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append((font, info.codepoint, x + pos.x_offset * scale, pos.y_offset * scale, scale))
            x += pos.x_advance * scale + tracking
    return glyphs, x - (tracking if glyphs else 0)


def measure(text, size, key="serif", axes=None, tracking=0.0, cjk="sc") -> float:
    return _layout(text, size, key, axes or {}, tracking, cjk)[1]


def path(text, x, y, size, key="serif", axes=None, tracking=0.0, anchor="start", cjk="sc") -> str:
    """Return the `d` attribute for `text` with its baseline at (x, y)."""
    glyphs, width = _layout(text, size, key, axes or {}, tracking, cjk)
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    for font, gid, gx, gy, s in glyphs:
        font.draw_glyph_with_pen(gid, TransformPen(pen, (s, 0, 0, -s, x + gx, y - gy)))
    return pen.getCommands()


def glyph_table(chars: str, size: float, key: str, axes=None) -> dict:
    """Outline each char at the origin: {char: {"d": ..., "adv": ...}}.

    Lets CI scripts compose numbers and labels without the font files.
    """
    out = {}
    for ch in chars:
        out[ch] = {"d": path(ch, 0, 0, size, key, axes), "adv": round(measure(ch, size, key, axes), 2)}
    return out

#!/usr/bin/env python3
"""Generate the profile artwork in assets/.

    python3 design/build.py

Theme: ink on rice paper. The hero writes the ZH signature and fills the ONE STEP
practice squares, then closes with a cinnabar seal. The AXIORA figure
sends ink through the project's architecture. All lettering uses outlines and
animated with SMIL, which GitHub's image proxy leaves intact. Each figure also
gets a *-still.svg that the README's <picture> serves under prefers-reduced-motion.

It also writes assets/glyphs.json, the outlines the daily ink-calendar job
(.github/scripts/ink_calendar.py) uses, so CI never needs the font files.

Fonts (OFL, from github.com/google/fonts, saved into design/fonts/, not committed):
  Fraunces.ttf        <- ofl/fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf
  FrauncesItalic.ttf  <- ofl/fraunces/Fraunces-Italic[SOFT,WONK,opsz,wght].ttf
  Mono.ttf            <- ofl/jetbrainsmono/JetBrainsMono[wght].ttf
Requires: pip install uharfbuzz fonttools
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import svgtext as ST

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Paper, ink and cinnabar, the three materials of a signed page.
PALETTES = {
    "light": {
        "paper": "#F4EEE2",
        "edge": "#E2D8C4",
        "ink": "#1E1C19",
        "ink2": "#3F3A33",
        "muted": "#7D7364",
        "wash": "#C9BEA9",
        "grid": "#D9A497",
        "cinnabar": "#B5382A",
        "seal_text": "#F4EEE2",
        "grain": 0.07,
    },
    "dark": {
        "paper": "#1A1917",
        "edge": "#2C2A26",
        "ink": "#EEE7D7",
        "ink2": "#CFC6B4",
        "muted": "#958C7C",
        "wash": "#4D4840",
        "grid": "#6B3A31",
        "cinnabar": "#E0604B",
        "seal_text": "#1A1917",
        "grain": 0.09,
    },
}

SERIF = {"opsz": 144, "wght": 560, "SOFT": 100, "WONK": 1}
SERIF_BODY = {"opsz": 24, "wght": 420, "SOFT": 50, "WONK": 0}
MONO = {"wght": 450}


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def text(t, x, y, size, key="serif", axes=None, fill="ink", anchor="start", tracking=0.0, extra=""):
    d = ST.path(t, x, y, size, key, axes, tracking, anchor)
    return f'<path class="{fill}" d="{d}"{extra}/>'


def style(pal) -> str:
    rules = " ".join(
        f".{k}{{fill:{v}}}" for k, v in pal.items() if isinstance(v, str)
    )
    return f"<style>{rules}</style>"


def paper_defs(pal, w, h) -> str:
    """Background with a faint paper grain (fractal noise, no images)."""
    return (
        f'<filter id="grain" x="0" y="0" width="100%" height="100%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" stitchTiles="stitch"/>'
        f'<feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.28  0 0 0 {pal["grain"]} 0"/>'
        f"</filter>"
        f'<filter id="bleed" x="-10%" y="-10%" width="120%" height="120%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="2" seed="3"/>'
        f'<feDisplacementMap in="SourceGraphic" scale="9"/>'
        f"</filter>"
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="22"/></clipPath>'
    )


def paper(w, h) -> str:
    return (
        f'<rect class="paper" width="{w}" height="{h}" rx="22"/>'
        f'<rect width="{w}" height="{h}" rx="22" filter="url(#grain)"/>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="21.5" fill="none" stroke-width="1.5" class="edge-stroke"/>'
    )


def svg(w, h, pal, defs, body, label) -> str:
    css = style(pal) + f"<style>.edge-stroke{{stroke:{pal['edge']}}}</style>"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{label}">{css}<defs>{paper_defs(pal, w, h)}{defs}</defs>'
        f'<g clip-path="url(#card)">{paper(w, h)}{body}</g></svg>\n'
    )


# --------------------------------------------------------------------------- hero
#
# Two vertical columns read ONE and STEP, with the seal below ONE.
# Each letter sits in a practice square and is revealed through a mask:
# a wide brush sweeps across the square in three passes, its edge roughened by a
# displacement filter so the ink looks absorbed rather than wiped on. When a
# character finishes, a faint ring spreads from it like ink settling into paper.

HW, HH = 1280, 440
CYCLE = 11.0  # seconds per loop
CELL = 76.0  # practice-square size
CH = 62.0  # character size
MOTTO = "A little better every day."
COLS = [  # (x of column centre, characters)
    (1060.0, "ONE"),
    (1150.0, "STEP"),
]
TOP = 36.0
PITCH = 84.0
T0, DT, WRITE = 0.6, 0.62, 0.5  # first char start, gap between chars, write time
SEAL_AT = T0 + DT * 7 + 0.15
FADE = (0.91, 0.965)  # share of the cycle where the page clears

# Each signature stroke pairs a pressure-shaped outline with its pen trajectory
# and finishing time. Both themes and the static version use the same outlines.
SIGNATURE = (
    (
        "M91 169 C95 152 115 138 147 134 C191 127 235 137 272 119 "
        "C282 114 289 117 285 126 C268 147 224 169 188 192 "
        "C164 207 145 223 133 237 C157 232 181 230 205 234 "
        "C233 239 260 238 288 224 C267 246 240 255 209 252 "
        "C176 249 150 246 120 257 C109 261 102 255 109 245 "
        "C139 200 216 161 257 134 C219 147 183 140 149 143 "
        "C121 145 101 155 91 169 Z",
        "M91 169 C101 148 125 141 149 139 C196 132 238 143 282 120 "
        "C243 158 154 193 115 252 C156 236 177 241 209 243 C240 248 269 238 288 224",
        1.24,
    ),
    (
        "M299 166 C306 148 331 126 354 119 C367 115 377 119 371 130 "
        "C351 162 328 193 312 225 C305 240 307 249 317 251 "
        "C299 257 288 245 296 226 C310 194 339 157 357 131 "
        "C334 135 313 147 299 166 Z",
        "M299 166 C316 139 348 123 366 124 C347 155 313 202 304 229 "
        "C298 244 303 250 317 251",
        1.83,
    ),
    (
        "M444 154 C455 138 474 121 489 116 C503 111 510 118 501 131 "
        "C474 169 444 198 426 224 C415 240 420 246 435 247 "
        "C461 247 498 236 532 215 C507 240 472 255 437 259 "
        "C412 262 395 251 408 229 C426 198 461 159 488 126 "
        "C470 130 456 142 444 154 Z",
        "M444 154 C465 130 491 115 498 121 C486 144 438 194 417 230 "
        "C406 247 420 254 436 253 C472 251 508 234 532 215",
        2.58,
    ),
    (
        "M275 215 C310 193 372 179 426 176 C448 175 463 174 478 168 "
        "C467 179 450 184 425 187 C365 192 318 197 275 215 Z",
        "M275 215 C310 196 370 186 426 181 C447 179 465 178 478 168",
        3.03,
    ),
)


def kt(t: float) -> str:
    return f"{t / CYCLE:.4f}"


def signature(still: bool) -> tuple[str, str]:
    defs, strokes = [], []
    start = 0.18
    for i, (outline, trace, end) in enumerate(SIGNATURE):
        if still:
            strokes.append(f'<path d="{outline}"/>')
            continue
        mask_id = f"signature-{i}"
        defs.append(
            f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="0" y="0" width="{HW}" height="{HH}">'
            f'<path d="{trace}" fill="none" stroke="#fff" stroke-width="36" stroke-linecap="round" '
            f'stroke-linejoin="round" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="1.1">'
            f'<animate attributeName="stroke-dashoffset" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
            f'keyTimes="0;{kt(start)};{kt(end)};1" values="1.1;1.1;0;0"/></path></mask>'
        )
        strokes.append(f'<path d="{outline}" mask="url(#{mask_id})"/>')
        start = end
    if not still:
        strokes.append(
            f'<animate attributeName="opacity" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
            f'keyTimes="0;{FADE[0]};{FADE[1]};1" values="1;1;0;0"/>'
        )
    return "".join(defs), f'<g class="ink">{"".join(strokes)}</g>'


def cells():
    out = []
    for cx, chars in COLS:
        for i, ch in enumerate(chars):
            out.append((ch, cx, TOP + i * PITCH + CELL / 2))
    return out


def practice_square(cx, cy) -> str:
    h = CELL / 2
    x0, y0 = cx - h, cy - h
    dash = 'stroke-dasharray="3 4"'
    return (
        f'<rect x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(CELL)}" height="{fmt(CELL)}" fill="none" stroke-width="1.2"/>'
        f'<path d="M{fmt(cx)} {fmt(y0)}V{fmt(y0 + CELL)}M{fmt(x0)} {fmt(cy)}H{fmt(x0 + CELL)}" {dash} stroke-width="0.9"/>'
        f'<path d="M{fmt(x0)} {fmt(y0)}L{fmt(x0 + CELL)} {fmt(y0 + CELL)}M{fmt(x0 + CELL)} {fmt(y0)}L{fmt(x0)} {fmt(y0 + CELL)}" {dash} stroke-width="0.7" opacity="0.6"/>'
    )


def brush_path(cx, cy) -> str:
    """Three horizontal passes covering the square, top to bottom."""
    h = CELL / 2 + 4
    ys = [cy - h + 14, cy, cy + h - 14]
    pts = []
    for i, y in enumerate(ys):
        a, b = (cx - h, cx + h) if i % 2 == 0 else (cx + h, cx - h)
        pts += [(a, y), (b, y)]
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)


def hero(pal, still: bool) -> str:
    defs, body = [], []

    # Left: name, line, tagline.
    body.append(text("ZH-S-2115", 98, 112, 17, "mono", MONO, "muted", tracking=3.2))
    signature_defs, signature_body = signature(still)
    defs.append(signature_defs)
    body.append(signature_body)
    body.append(
        text("Building AXIORA, a self-hosted agent workbench.", 98, 292, 27, "serif-italic", SERIF_BODY, "ink2")
    )
    body.append(text(MOTTO, 98, 362, 30, "serif-italic", SERIF_BODY, "ink"))
    # A cinnabar brush stroke under the tagline, drawn once per cycle.
    stroke = "M100 384 C202 379 304 381 410 386"
    if still:
        body.append(f'<path d="{stroke}" fill="none" stroke="{pal["cinnabar"]}" stroke-width="5" stroke-linecap="round"/>')
    else:
        body.append(
            f'<path d="{stroke}" fill="none" stroke="{pal["cinnabar"]}" stroke-width="5" stroke-linecap="round" '
            f'pathLength="1" stroke-dasharray="1 1.1" stroke-dashoffset="1.05">'
            f'<animate attributeName="stroke-dashoffset" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
            f'keyTimes="0;{kt(SEAL_AT + 0.3)};{kt(SEAL_AT + 1.0)};{FADE[1]};1" values="1.05;1.05;0;0;1.05" '
            f'calcMode="spline" keySplines="0 0 1 1;.3 0 .2 1;0 0 1 1;0 0 1 1"/></path>'
        )

    # Caption, bottom right.
    body.append(
        text("Drop by drop, ink becomes words", 1188, 410, 15, "serif-italic", SERIF_BODY, "muted", anchor="end")
    )

    # Practice squares.
    sq = "".join(practice_square(cx, cy) for _, cx, cy in cells())
    body.append(f'<g stroke="{pal["grid"]}" opacity="0.75">{sq}</g>')

    # Characters, ripples, masks.
    chars, ripples = [], []
    for i, (ch, cx, cy) in enumerate(cells()):
        d = ST.path(ch, cx, cy + CH * 0.36, CH, "serif-italic", SERIF, 0, "middle")
        if still:
            chars.append(f'<path class="ink" d="{d}"/>')
            continue
        t1 = T0 + i * DT
        t2 = t1 + WRITE
        mid = f"m{i}"
        defs.append(
            f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{HW}" height="{HH}">'
            f'<path d="{brush_path(cx, cy)}" fill="none" stroke="#fff" stroke-width="36" stroke-linecap="round" '
            f'stroke-linejoin="round" pathLength="1" stroke-dasharray="1 1.1" stroke-dashoffset="1.05" filter="url(#bleed)">'
            f'<animate attributeName="stroke-dashoffset" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
            f'keyTimes="0;{kt(t1)};{kt(t2)};{FADE[1]};1" values="1.05;1.05;0;0;1.05" '
            f'calcMode="spline" keySplines="0 0 1 1;.45 .05 .55 .95;0 0 1 1;0 0 1 1"/></path></mask>'
        )
        chars.append(f'<path class="ink" d="{d}" mask="url(#{mid})"/>')
        # Ripple once the character settles.
        r0, r1, r2 = kt(t2 - 0.01), kt(t2), kt(t2 + 1.1)
        ripples.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="24" fill="none" stroke="{pal["ink"]}" stroke-width="1.2" opacity="0">'
            f'<animate attributeName="r" dur="{fmt(CYCLE)}s" repeatCount="indefinite" keyTimes="0;{r1};{r2};1" values="24;24;62;62"/>'
            f'<animate attributeName="opacity" dur="{fmt(CYCLE)}s" repeatCount="indefinite" keyTimes="0;{r0};{r1};{r2};1" values="0;0;0.32;0;0"/>'
            f"</circle>"
        )

    fade = (
        ""
        if still
        else f'<animate attributeName="opacity" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
        f'keyTimes="0;{FADE[0]};{FADE[1]};1" values="1;1;0;0"/>'
    )
    body.append(f"<g>{''.join(ripples)}</g>")
    body.append(f"<g>{fade}{''.join(chars)}</g>")

    # The cinnabar seal carries the initials and is stamped last.
    sx, sy, ss = 1060.0, TOP + 3 * PITCH + CELL / 2, 58.0
    initials = ST.path("ZH", 0, 10, 28, "serif", {"opsz": 14, "wght": 700, "SOFT": 0, "WONK": 0}, 1.5, "middle")
    seal = (
        f'<rect x="{fmt(-ss / 2)}" y="{fmt(-ss / 2)}" width="{fmt(ss)}" height="{fmt(ss)}" rx="5" '
        f'fill="{pal["cinnabar"]}" filter="url(#bleed)"/>'
        f'<path class="seal_text" d="{initials}" opacity="0.9"/>'
    )
    # Seal drawn around its own centre so the stamp can scale in place.
    if still:
        body.append(f'<g transform="translate({fmt(sx)} {fmt(sy)}) rotate(-4)">{seal}</g>')
    else:
        a, b, c = kt(SEAL_AT), kt(SEAL_AT + 0.14), kt(SEAL_AT + 0.32)
        body.append(
            f'<g transform="translate({fmt(sx)} {fmt(sy)}) rotate(-4)"><g opacity="0">'
            f'<animate attributeName="opacity" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
            f'keyTimes="0;{a};{b};{FADE[0]};{FADE[1]};1" values="0;0;1;1;0;0"/>'
            f'<animateTransform attributeName="transform" type="scale" dur="{fmt(CYCLE)}s" repeatCount="indefinite" '
            f'keyTimes="0;{a};{b};{c};1" values="1.6;1.6;0.94;1;1"/>'
            f"{seal}</g></g>"
        )

    label = (
        f"ZH in brush calligraphy. Building AXIORA, a self-hosted agent workbench. {MOTTO} "
        "The letters of ONE STEP fill the practice squares beside a red ZH seal."
    )
    return svg(HW, HH, pal, "".join(defs), "".join(body), label)


# ------------------------------------------------------------------------- AXIORA
#
# Message entry points on the left; ink flows into the AXIORA backend, through one
# of the three registries (Workspace, Capability, Channel), into the Pi Agent
# Runner, and a cinnabar reply flows back to where the message came from.

AW, AH = 1280, 470
ACYCLE = 13.5
ENTRIES = ["Web", "Desktop", "Feishu", "Telegram", "QQ", "DingTalk", "WeChat", "Discord", "WhatsApp"]
EY0, EDY = 66.0, 41.0
EDOT_X = 214.0
BK = (390.0, 175.0, 250.0, 120.0)  # backend x, y, w, h
REG = [  # title, subtitle, centre y
    ("Workspace", "Session · Memory · Files", 110.0),
    ("Capability", "Skills · MCP · Plugins", 235.0),
    ("Channel", "Binding · ACL · Delivery", 360.0),
]
RX, RW, RH = 742.0, 196.0, 74.0
RUN = (1018.0, 180.0, 226.0, 110.0)
# (entry index, registry index) for each trip in a cycle.
TRIPS = [(2, 1), (0, 0), (3, 2)]
SLOT = ACYCLE / len(TRIPS)


def entry_y(i):
    return EY0 + i * EDY


def bez(p0, p1, p2, p3, n=24):
    return [
        (
            (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
            (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1],
        )
        for t in (k / n for k in range(n + 1))
    ]


def plen(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def trip_geometry(e, r):
    """Return (d, fractions of length where the trip enters backend, registry, runner)."""
    ey = entry_y(e)
    bx, by, bw, bh = BK
    bcy = by + bh / 2
    ry = REG[r][2]
    rx, _, _, _ = RUN
    run_cy = RUN[1] + RUN[3] / 2
    segs = [
        bez((EDOT_X, ey), (EDOT_X + 90, ey), (bx - 90, bcy), (bx, bcy)),
        [(bx, bcy), (bx + bw, bcy)],
        bez((bx + bw, bcy), (bx + bw + 55, bcy), (RX - 55, ry), (RX, ry)),
        [(RX, ry), (RX + RW, ry)],
        bez((RX + RW, ry), (RX + RW + 50, ry), (rx - 50, run_cy), (rx, run_cy)),
        [(rx, run_cy), (rx + 40, run_cy)],
    ]
    lens = [plen(s) for s in segs]
    total = sum(lens)
    marks = [lens[0] / total, sum(lens[:3]) / total, sum(lens[:5]) / total]
    d = (
        f"M{fmt(EDOT_X)} {fmt(ey)} C{fmt(EDOT_X + 90)} {fmt(ey)} {fmt(bx - 90)} {fmt(bcy)} {fmt(bx)} {fmt(bcy)} "
        f"L{fmt(bx + bw)} {fmt(bcy)} C{fmt(bx + bw + 55)} {fmt(bcy)} {fmt(RX - 55)} {fmt(ry)} {fmt(RX)} {fmt(ry)} "
        f"L{fmt(RX + RW)} {fmt(ry)} C{fmt(RX + RW + 50)} {fmt(ry)} {fmt(rx - 50)} {fmt(run_cy)} {fmt(rx)} {fmt(run_cy)} "
        f"L{fmt(rx + 40)} {fmt(run_cy)}"
    )
    return d, marks


def box(x, y, w, h, pal, cls="paper") -> str:
    return (
        f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="8" class="{cls}" '
        f'stroke="{pal["ink2"]}" stroke-width="1.4"/>'
    )


def flash(x, y, w, h, pal, times) -> str:
    """Cinnabar outline that lights up at each time in `times` (seconds)."""
    if not times:
        return ""
    kts, vals = ["0"], ["0"]
    for t in sorted(times):
        for dt, v in ((-0.05, 0), (0.12, 1), (0.9, 0)):
            kts.append(f"{max(0.0, t + dt) / ACYCLE:.4f}")
            vals.append(str(v))
    kts.append("1")
    vals.append("0")
    return (
        f'<rect x="{fmt(x - 3)}" y="{fmt(y - 3)}" width="{fmt(w + 6)}" height="{fmt(h + 6)}" rx="10" fill="none" '
        f'stroke="{pal["cinnabar"]}" stroke-width="2" opacity="0">'
        f'<animate attributeName="opacity" dur="{fmt(ACYCLE)}s" repeatCount="indefinite" '
        f'keyTimes="{";".join(kts)}" values="{";".join(vals)}"/></rect>'
    )


def axiora(pal, still: bool) -> str:
    body = []
    bx, by, bw, bh = BK
    bcy = by + bh / 2
    run_x, run_y, run_w, run_h = RUN
    run_cy = run_y + run_h / 2

    # Column labels.
    body.append(text("ENTRY POINTS", 60, 36, 12, "mono", MONO, "muted", tracking=2.4))
    body.append(text("REGISTRIES", RX, 36, 12, "mono", MONO, "muted", tracking=2.4))

    # Wash lines (static): every entry to the backend, backend to registries, registries to runner.
    lines = []
    for i in range(len(ENTRIES)):
        ey = entry_y(i)
        lines.append(f"M{fmt(EDOT_X)} {fmt(ey)} C{fmt(EDOT_X + 90)} {fmt(ey)} {fmt(bx - 90)} {fmt(bcy)} {fmt(bx)} {fmt(bcy)}")
    for _, _, ry in REG:
        lines.append(f"M{fmt(bx + bw)} {fmt(bcy)} C{fmt(bx + bw + 55)} {fmt(bcy)} {fmt(RX - 55)} {fmt(ry)} {fmt(RX)} {fmt(ry)}")
        lines.append(f"M{fmt(RX + RW)} {fmt(ry)} C{fmt(RX + RW + 50)} {fmt(ry)} {fmt(run_x - 50)} {fmt(run_cy)} {fmt(run_x)} {fmt(run_cy)}")
    body.append(f'<path d="{" ".join(lines)}" fill="none" stroke="{pal["wash"]}" stroke-width="1.3"/>')

    # Ink trips (drawn under the boxes so the stroke disappears inside them).
    flashes = {"bk": [], "run": [], 0: [], 1: [], 2: []}
    entry_hits = {}
    fwd, back = 2.1, 1.7
    for k, (e, r) in enumerate(TRIPS):
        d, marks = trip_geometry(e, r)
        t0 = k * SLOT + 0.3
        t1 = t0 + fwd
        t2 = t1 + 0.55
        t3 = t2 + back
        flashes["bk"] += [t0 + fwd * marks[0], t2 + back * (1 - marks[0])]
        flashes[r] += [t0 + fwd * marks[1]]
        flashes["run"] += [t0 + fwd * marks[2]]
        entry_hits.setdefault(e, []).append(t3)
        if still:
            continue
        L = 0.09
        for color, a, b, v0, v1, w in (
            (pal["ink"], t0, t1, L, -1, 3.2),
            (pal["cinnabar"], t2, t3, -1, L, 2.6),
        ):
            body.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" pathLength="1" '
                f'stroke-dasharray="{L} 2" stroke-dashoffset="{v0}">'
                f'<animate attributeName="stroke-dashoffset" dur="{fmt(ACYCLE)}s" repeatCount="indefinite" '
                f'keyTimes="0;{a / ACYCLE:.4f};{b / ACYCLE:.4f};1" values="{v0};{v0};{v1};{v1}" '
                f'calcMode="spline" keySplines="0 0 1 1;.5 0 .5 1;0 0 1 1"/></path>'
            )

    # Entry labels and dots.
    for i, name in enumerate(ENTRIES):
        ey = entry_y(i)
        body.append(text(name, EDOT_X - 22, ey + 6, 18, "serif", SERIF_BODY, "ink2", anchor="end"))
        body.append(f'<circle cx="{fmt(EDOT_X)}" cy="{fmt(ey)}" r="4" class="ink2"/>')
        if not still and i in entry_hits:
            for t in entry_hits[i]:
                a, b = t / ACYCLE, min(t + 1.2, ACYCLE) / ACYCLE
                body.append(
                    f'<circle cx="{fmt(EDOT_X)}" cy="{fmt(ey)}" r="4" fill="none" stroke="{pal["cinnabar"]}" stroke-width="1.6" opacity="0">'
                    f'<animate attributeName="r" dur="{fmt(ACYCLE)}s" repeatCount="indefinite" keyTimes="0;{a:.4f};{b:.4f};1" values="4;4;22;22"/>'
                    f'<animate attributeName="opacity" dur="{fmt(ACYCLE)}s" repeatCount="indefinite" keyTimes="0;{max(a - 0.001, 0):.4f};{a:.4f};{b:.4f};1" values="0;0;0.9;0;0"/>'
                    f"</circle>"
                )

    # Backend.
    body.append(box(bx, by, bw, bh, pal))
    body.append(text("AXIORA", bx + bw / 2, by + 62, 44, "serif", SERIF, "ink", anchor="middle", tracking=1))
    body.append(text("Auth · API · Queue · Scheduler", bx + bw / 2, by + 90, 12.5, "mono", MONO, "muted", anchor="middle"))
    # Small seal on the backend's corner.
    body.append(
        f'<rect x="{fmt(bx + bw - 22)}" y="{fmt(by - 10)}" width="28" height="28" rx="3" fill="{pal["cinnabar"]}" '
        f'transform="rotate(6 {fmt(bx + bw - 8)} {fmt(by + 4)})"/>'
        f'<path class="seal_text" transform="rotate(6 {fmt(bx + bw - 8)} {fmt(by + 4)})" '
        f'd="{ST.path("A", bx + bw - 8, by + 11, 20, "serif", SERIF, 0, "middle")}"/>'
    )
    body.append(text("self-hosted backend", bx + bw / 2, by + bh + 28, 15, "serif-italic", SERIF_BODY, "muted", anchor="middle"))

    # Registries.
    for i, (title, sub, ry) in enumerate(REG):
        y = ry - RH / 2
        body.append(box(RX, y, RW, RH, pal))
        body.append(text(title, RX + 18, y + 33, 22, "serif", SERIF_BODY, "ink"))
        body.append(text(sub, RX + 18, y + 56, 12, "mono", MONO, "muted"))

    # Runner.
    body.append(box(run_x, run_y, run_w, run_h, pal))
    body.append(text("Pi Agent Runner", run_x + run_w / 2, run_y + 42, 22, "serif", SERIF_BODY, "ink", anchor="middle"))
    body.append(text("Host / Docker", run_x + run_w / 2, run_y + 66, 13, "mono", MONO, "muted", anchor="middle"))
    body.append(text("Tools · Extensions · Subagents", run_x + run_w / 2, run_y + 88, 11.5, "mono", MONO, "muted", anchor="middle"))
    body.append(text("agent runtime", run_x + run_w / 2, run_y + run_h + 28, 15, "serif-italic", SERIF_BODY, "muted", anchor="middle"))

    if not still:
        body.append(flash(bx, by, bw, bh, pal, flashes["bk"]))
        for i, (_, _, ry) in enumerate(REG):
            body.append(flash(RX, ry - RH / 2, RW, RH, pal, flashes[i]))
        body.append(flash(run_x, run_y, run_w, run_h, pal, flashes["run"]))

    body.append(
        text("one agent, one workspace, every channel", AW - 52, AH - 30, 15, "serif-italic", SERIF_BODY, "muted", anchor="end")
    )

    label = (
        "Messages from Web, Desktop, Feishu, Telegram, QQ, DingTalk, WeChat, Discord and WhatsApp flow into the "
        "AXIORA backend, through the Workspace, Capability or Channel registry, into the Pi Agent Runner on the host "
        "or in Docker, and the reply flows back to where the message came from."
    )
    return svg(AW, AH, pal, "", "".join(body), label)


# ------------------------------------------------------------------ glyph table
#
# Outlines the ink-calendar job composes at run time.

GLYPH_SETS = {
    "num": ("0123456789,", 40, "serif", SERIF),
    "label": ("0123456789,abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ·-:", 14, "mono", MONO),
}
STATIC = {
    "title": ("Ink Calendar", 30, "serif-italic", SERIF_BODY),
    "contributions": ("contributions in the last year", 18, "serif-italic", SERIF_BODY),
    "streak": ("day streak", 18, "serif-italic", SERIF_BODY),
    "longest": ("longest streak", 18, "serif-italic", SERIF_BODY),
    "caption": ("One ink dot per day", 14, "serif-italic", SERIF_BODY),
}


def glyphs() -> dict:
    out = {"sets": {}, "static": {}}
    for name, (chars, size, key, axes) in GLYPH_SETS.items():
        out["sets"][name] = {"size": size, "glyphs": ST.glyph_table(chars, size, key, axes)}
    for name, (t, size, key, axes) in STATIC.items():
        out["static"][name] = {"d": ST.path(t, 0, 0, size, key, axes), "w": round(ST.measure(t, size, key, axes), 2)}
    return out


def main():
    ASSETS.mkdir(exist_ok=True)
    for mode, pal in PALETTES.items():
        for still in (False, True):
            sfx = "-still" if still else ""
            (ASSETS / f"hero-{mode}{sfx}.svg").write_text(hero(pal, still))
            (ASSETS / f"axiora-{mode}{sfx}.svg").write_text(axiora(pal, still))
    (ASSETS / "glyphs.json").write_text(json.dumps(glyphs(), ensure_ascii=False, separators=(",", ":")))
    for p in sorted(ASSETS.iterdir()):
        print(f"{p.stat().st_size // 1024:>5} KB  {p.name}")


if __name__ == "__main__":
    main()

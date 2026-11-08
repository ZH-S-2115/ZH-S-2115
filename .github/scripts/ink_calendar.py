#!/usr/bin/env python3
"""Draw the contribution calendar as ink drops on rice paper.

    GH_TOKEN=... PROFILE_OWNER=ZH-S-2115 python3 .github/scripts/ink_calendar.py
    python3 .github/scripts/ink_calendar.py --sample   # offline, fake data
    gh api graphql -f query=... -f login=ZH-S-2115 > cal.json
    python3 .github/scripts/ink_calendar.py --from cal.json

Each day is one drop: the more contributions, the larger and darker the drop.
In the animated version the drops fall week by week from left to right and
spread a little as they land, as ink does on xuan paper; today's drop is
cinnabar. Writes assets/ink-{light,dark}.svg and their *-still.svg twins.

Stdlib only. Text comes from assets/glyphs.json (built by design/build.py), so
this job needs no font files.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

PALETTES = {
    "light": {"paper": "#F4EEE2", "edge": "#E2D8C4", "ink": "#1E1C19", "muted": "#7D7364",
              "wash": "#E4DACB", "cinnabar": "#B5382A", "grain": 0.07},
    "dark": {"paper": "#1A1917", "edge": "#2C2A26", "ink": "#EEE7D7", "muted": "#958C7C",
             "wash": "#2A2824", "cinnabar": "#E0604B", "grain": 0.09},
}

W, H = 1280, 320
GX, GY, STEP = 132.0, 116.0, 19.4  # grid origin and pitch
RADII = [2.0, 4.4, 5.9, 7.2, 8.6]  # by level 0..4
ALPHA = [0.22, 0.42, 0.62, 0.82, 1.0]
WEEK_T = 0.11  # seconds between weeks falling
HOLD = 5.0  # seconds the full page stays before it clears

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch(login: str, token: str):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]]) for d in w["contributionDays"]]
        for w in cal["weeks"]
    ]
    return cal["totalContributions"], weeks


def sample():
    rnd = random.Random(2115)
    end = dt.date(2026, 11, 8)
    start = end - dt.timedelta(days=364 + (end.weekday() + 1) % 7)
    weeks, day, total = [], start, 0
    while day <= end:
        if day.weekday() == 6 or not weeks:
            weeks.append([])
        n = 0 if rnd.random() < 0.45 else rnd.choice([1, 1, 2, 3, 4, 6, 9])
        total += n
        lvl = 0 if n == 0 else 1 if n < 2 else 2 if n < 4 else 3 if n < 6 else 4
        weeks[-1].append((day.isoformat(), n, lvl))
        day += dt.timedelta(days=1)
    return total, weeks


def streaks(weeks):
    days = [d for w in weeks for d in w]
    longest = run = 0
    for _, n, _ in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    # Today may still be empty; the streak counts until yesterday in that case.
    tail = days[:-1] if days and days[-1][1] == 0 else days
    for _, n, _ in reversed(tail):
        if not n:
            break
        current += 1
    return current, longest


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Glyphs:
    def __init__(self, path: Path):
        self.data = json.loads(path.read_text())

    def word(self, set_name: str, s: str, x: float, y: float, anchor="start", scale=1.0):
        g = self.data["sets"][set_name]["glyphs"]
        width = sum(g[c]["adv"] for c in s) * scale
        if anchor == "end":
            x -= width
        elif anchor == "middle":
            x -= width / 2
        out, cx = [], x
        for c in s:
            if g[c]["d"]:
                out.append(f'<path transform="translate({fmt(cx)} {fmt(y)}) scale({fmt(scale)})" d="{g[c]["d"]}"/>')
            cx += g[c]["adv"] * scale
        return "".join(out), width

    def static(self, name: str, x: float, y: float, anchor="start"):
        s = self.data["static"][name]
        if anchor == "end":
            x -= s["w"]
        elif anchor == "middle":
            x -= s["w"] / 2
        return f'<path transform="translate({fmt(x)} {fmt(y)})" d="{s["d"]}"/>', s["w"]


def render(pal, still: bool, total: int, weeks, G: Glyphs) -> str:
    current, longest = streaks(weeks)
    cycle = len(weeks) * WEEK_T + 0.9 + HOLD + 0.8
    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="{total} contributions in the last year, drawn as one ink drop per day. '
        f'Current streak {current} days, longest {longest} days.">'
        f'<defs><filter id="grain" x="0" y="0" width="100%" height="100%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" stitchTiles="stitch"/>'
        f'<feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.28  0 0 0 {pal["grain"]} 0"/></filter>'
        f'<filter id="bleed" x="-30%" y="-30%" width="160%" height="160%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="2" seed="11"/>'
        f'<feDisplacementMap in="SourceGraphic" scale="3.2"/></filter>'
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath></defs>'
        f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" rx="22" fill="{pal["paper"]}"/>'
        f'<rect width="{W}" height="{H}" rx="22" filter="url(#grain)"/>'
        f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="21.5" fill="none" stroke="{pal["edge"]}" stroke-width="1.5"/>'
    )

    # Header: 墨迹 in brush, then the numbers.
    title, _ = G.static("title", GX, 58)
    out.append(f'<g fill="{pal["ink"]}">{title}</g>')
    x = W - 132
    stats = [(f"{longest:,}", "longest"), (f"{current:,}", "streak"), (f"{total:,}", "contributions")]
    parts = []
    for num, lab in stats:
        lp, lw = G.static(lab, x, 58, "end")
        np_, nw = G.word("num", num, x - lw - 10, 58, "end", 0.8)
        parts.append(f'<g fill="{pal["muted"]}">{lp}</g><g fill="{pal["ink"]}">{np_}</g>')
        x -= lw + nw + 44
    out.append("".join(parts))

    # Month labels.
    last_month = None
    labels = []
    for wi, w in enumerate(weeks):
        m = dt.date.fromisoformat(w[0][0]).strftime("%b")
        if m != last_month and wi < len(weeks) - 2:
            p, _ = G.word("label", m, GX + wi * STEP - 4, GY - 14, "start", 0.85)
            labels.append(p)
            last_month = m
    out.append(f'<g fill="{pal["muted"]}">{"".join(labels)}</g>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        p, _ = G.word("label", name, GX - 16, GY + row * STEP + 4.5, "end", 0.85)
        out.append(f'<g fill="{pal["muted"]}">{p}</g>')

    # Drops. Grid wash first so empty days still read as paper squares.
    wash, drops = [], []
    today = weeks[-1][-1][0]
    for wi, w in enumerate(weeks):
        wd0 = dt.date.fromisoformat(w[0][0]).isoweekday() % 7  # first week may start mid-week
        for k, (date, n, lvl) in enumerate(w):
            cx, cy = GX + wi * STEP, GY + (wd0 + k) * STEP
            wash.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="2"/>')
            if lvl == 0:
                continue
            r = RADII[lvl]
            colour = pal["cinnabar"] if date == today else pal["ink"]
            a = ALPHA[lvl]
            if still:
                drops.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" fill="{colour}" fill-opacity="{a}"/>')
                continue
            t0 = wi * WEEK_T + k * 0.012
            k0, k1, k2 = t0 / cycle, (t0 + 0.18) / cycle, (t0 + 0.7) / cycle
            f0, f1 = (cycle - 0.8) / cycle, (cycle - 0.25) / cycle
            drops.append(
                f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="0" fill="{colour}" fill-opacity="{a}">'
                f'<animate attributeName="r" dur="{fmt(cycle)}s" repeatCount="indefinite" '
                f'keyTimes="0;{k0:.4f};{k1:.4f};{k2:.4f};{f0:.4f};{f1:.4f};1" '
                f'values="0;0;{fmt(r * 0.55)};{fmt(r)};{fmt(r)};{fmt(r * 1.15)};0"/>'
                f'<animate attributeName="cy" dur="{fmt(cycle)}s" repeatCount="indefinite" '
                f'keyTimes="0;{k0:.4f};{k1:.4f};1" values="{fmt(cy - 8)};{fmt(cy - 8)};{fmt(cy)};{fmt(cy)}"/>'
                f"</circle>"
            )
    out.append(f'<g fill="{pal["wash"]}">{"".join(wash)}</g>')
    out.append(f'<g filter="url(#bleed)">{"".join(drops)}</g>')

    # Legend + caption.
    ly = GY + 7 * STEP + 16
    cap, _ = G.static("caption", GX - 8, ly + 5)
    out.append(f'<g fill="{pal["muted"]}">{cap}</g>')
    lx = W - 132 - 5 * STEP
    for i in range(5):
        out.append(
            f'<circle cx="{fmt(lx + i * STEP)}" cy="{fmt(ly)}" r="{fmt(RADII[i])}" fill="{pal["ink"] if i else pal["wash"]}" '
            f'fill-opacity="{ALPHA[i] if i else 1}"/>'
        )
    out.append("</g></svg>\n")
    return "".join(out)


def main():
    if "--sample" in sys.argv:
        total, weeks = sample()
    elif "--from" in sys.argv:  # a saved GraphQL response, e.g. from `gh api graphql`
        body = json.loads(Path(sys.argv[sys.argv.index("--from") + 1]).read_text())
        cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        total = cal["totalContributions"]
        weeks = [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]]) for d in w["contributionDays"]]
                 for w in cal["weeks"]]
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        login = os.environ.get("PROFILE_OWNER")
        if not token or not login:
            raise SystemExit("set GH_TOKEN and PROFILE_OWNER, or pass --sample")
        total, weeks = fetch(login, token)
    G = Glyphs(ASSETS / "glyphs.json")
    for mode, pal in PALETTES.items():
        for still in (False, True):
            name = f"ink-{mode}{'-still' if still else ''}.svg"
            (ASSETS / name).write_text(render(pal, still, total, weeks, G))
            print(f"wrote assets/{name}")


if __name__ == "__main__":
    main()

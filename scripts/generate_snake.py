"""Generate an animated contribution-snake SVG from the GitHub contribution graph.

Fetches the last year of contributions for USER and writes one SVG per palette
(dark/light). The snake sweeps the grid column by column in a serpentine path,
"eating" each contribution cell as it passes. Pure SMIL animation, so it plays
inside GitHub's sanitized <img> rendering with no JavaScript.

Usage: python scripts/generate_snake.py
"""

import json
import urllib.request

USER = "jeev-jo"
API = f"https://github-contributions-api.jogruber.de/v4/{USER}?y=last"

CELL = 12          # cell edge, px
PITCH = 15         # cell edge + gap
PAD = 8            # canvas padding
STEP_SECONDS = 0.05  # snake speed: seconds per cell

PALETTES = {
    "dark": {
        "out": "assets/github-snake-dark.svg",
        "empty": "#161b22",
        "levels": ["#123c4d", "#155e75", "#0891b2", "#22d3ee"],
        "snake": ["#c4b5fd", "#a78bfa", "#8b5cf6", "#7c3aed"],
    },
    "light": {
        "out": "assets/github-snake.svg",
        "empty": "#ebedf0",
        "levels": ["#c7e0ff", "#79c0ff", "#388bfd", "#0969da"],
        "snake": ["#b392f0", "#8250df", "#6639ba", "#512a97"],
    },
}

WEEKDAY = {"Sun": 0, "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6}


def fetch_days():
    req = urllib.request.Request(API, headers={"User-Agent": "snake-generator"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data["contributions"]


def build_grid(days):
    """Map consecutive days onto (column, row) with GitHub's Sunday-first rows."""
    import datetime

    first = datetime.date.fromisoformat(days[0]["date"])
    w0 = (first.weekday() + 1) % 7  # Python: Mon=0 → GitHub: Sun=0
    cells = {}
    for i, day in enumerate(days):
        col, row = divmod(i + w0, 7)
        cells[(col, row)] = day["level"]
    n_cols = max(c for c, _ in cells) + 1
    return cells, n_cols


def serpentine(n_cols):
    """Visit order: column 0 top-down, column 1 bottom-up, ..."""
    order = []
    for col in range(n_cols):
        rows = range(7) if col % 2 == 0 else range(6, -1, -1)
        for row in rows:
            order.append((col, row))
    return order


def center(col, row):
    return PAD + col * PITCH + CELL / 2, PAD + row * PITCH + CELL / 2


def render(palette, cells, n_cols):
    order = serpentine(n_cols)
    total = len(order)
    dur = total * STEP_SECONDS
    width = PAD * 2 + n_cols * PITCH - (PITCH - CELL)
    height = PAD * 2 + 7 * PITCH - (PITCH - CELL)
    eat_time = {pos: i * STEP_SECONDS for i, pos in enumerate(order)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    ]

    # contribution cells; filled ones get eaten as the snake head arrives
    for (col, row), level in sorted(cells.items()):
        x, y = PAD + col * PITCH, PAD + row * PITCH
        if level == 0:
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{palette["empty"]}"/>'
            )
            continue
        color = palette["levels"][level - 1]
        t = eat_time[(col, row)] / dur
        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">'
            f'<animate attributeName="fill" values="{color};{palette["empty"]}" '
            f'keyTimes="0;{t:.4f}" calcMode="discrete" dur="{dur:.2f}s" '
            f'repeatCount="indefinite"/></rect>'
        )

    # snake path: cell centers in visit order, then off the right edge
    points = [center(c, r) for c, r in order]
    last_x, last_y = points[-1]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    path += f" L{last_x + 3 * PITCH:.1f},{last_y:.1f}"

    # body segments trail the head via negative begin offsets (phase shift)
    for seg, color in reversed(list(enumerate(palette["snake"]))):
        size = CELL if seg == 0 else CELL - 2
        half = size / 2
        delay = seg * 2.2 * STEP_SECONDS
        begin = "0s" if seg == 0 else f"-{dur - delay:.2f}s"
        parts.append(
            f'<rect x="{-half}" y="{-half}" width="{size}" height="{size}" rx="3" '
            f'fill="{color}"><animateMotion path="{path}" dur="{dur:.2f}s" '
            f'begin="{begin}" repeatCount="indefinite"/></rect>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main():
    days = fetch_days()
    cells, n_cols = build_grid(days)
    for name, palette in PALETTES.items():
        svg = render(palette, cells, n_cols)
        with open(palette["out"], "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{palette['out']}: {n_cols} weeks, {len(svg)} bytes ({name})")


if __name__ == "__main__":
    main()

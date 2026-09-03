"""Generate a self-hosted contribution-streak card (dark + light).

Replaces streak-stats.demolab.com, a shared public instance whose own
GitHub API quota is split across every profile using it — it periodically
exhausts that quota and renders a "Maximum retries exceeded... add PAT_1"
error until the quota resets. This script computes the same numbers
(total contributions, current streak, longest streak) directly from
GitHub's public contribution calendar and renders a static, self-contained
SVG — nothing at render time depends on a third party.

Usage: python scripts/generate_streak.py
"""

import re
import urllib.request
from datetime import date

USER = "jeev-jo"
URL = f"https://github.com/users/{USER}/contributions"

PALETTES = {
    "dark": {
        "out": "assets/streak-dark.svg",
        "bg": "#0d1117",
        "border": "#2b3a55",
        "number": "#22d3ee",
        "label": "#c9d1d9",
        "sub": "#7d8590",
        "ring_track": "#243352",
        "divider": "#2b3a55",
    },
    "light": {
        "out": "assets/streak-light.svg",
        "bg": "#ffffff",
        "border": "#d0d7de",
        "number": "#0969da",
        "label": "#24292f",
        "sub": "#57606a",
        "ring_track": "#e8eef7",
        "divider": "#d0d7de",
    },
}


def fetch_days():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 streak-generator"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode()

    dates = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"', html)
    tips = re.findall(r"(No contributions on|(\d+) contributions? on)", html)

    if len(dates) != len(tips):
        raise RuntimeError(f"date/tooltip count mismatch: {len(dates)} vs {len(tips)}")

    days = []
    for d, (_, count) in zip(dates, tips):
        days.append({"date": d, "count": int(count) if count else 0})
    days.sort(key=lambda x: x["date"])
    return days


def fmt(iso_date, with_year=True):
    y, m, d = (int(p) for p in iso_date.split("-"))
    text = date(y, m, d).strftime("%b ") + str(d)
    return f"{text}, {y}" if with_year else text


def compute_stats(days):
    total = sum(d["count"] for d in days)
    first_date = days[0]["date"]

    best_len, best_start, best_end = 0, None, None
    cur_len, cur_start = 0, None
    for d in days:
        if d["count"] > 0:
            if cur_len == 0:
                cur_start = d["date"]
            cur_len += 1
            if cur_len > best_len:
                best_len, best_start, best_end = cur_len, cur_start, d["date"]
        else:
            cur_len = 0

    n = len(days)
    last_idx = n - 1
    today_empty = days[last_idx]["count"] == 0
    yesterday_empty = last_idx > 0 and days[last_idx - 1]["count"] == 0

    if today_empty and yesterday_empty:
        current_len, current_start, current_end = 0, None, None
    else:
        end_idx = last_idx if not today_empty else last_idx - 1
        current_len = 0
        i = end_idx
        while i >= 0 and days[i]["count"] > 0:
            current_len += 1
            i -= 1
        current_start = days[end_idx - current_len + 1]["date"] if current_len else None
        current_end = days[end_idx]["date"] if current_len else None

    return {
        "total": total,
        "first_date": first_date,
        "longest": (best_len, best_start, best_end),
        "current": (current_len, current_start, current_end),
    }


def render(palette, stats):
    W, H = 700, 200
    total = stats["total"]
    cur_len, cur_start, cur_end = stats["current"]
    long_len, long_start, long_end = stats["longest"]

    total_range = f'{fmt(stats["first_date"])} - Present'
    cur_range = f"{fmt(cur_start)} - {fmt(cur_end)}" if cur_len else "-"
    long_range = f"{fmt(long_start)} - {fmt(long_end)}" if long_len else "-"

    col_w = W / 3
    ring_cx, ring_cy, ring_r = W / 2, 62, 32
    circumference = 2 * 3.14159265 * ring_r
    frac = min(cur_len / 30, 1.0)  # visual fill, caps out at a 30-day streak

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{palette["bg"]}" stroke="{palette["border"]}"/>
  <line x1="{col_w:.0f}" y1="28" x2="{col_w:.0f}" y2="{H-28}" stroke="{palette["divider"]}"/>
  <line x1="{2*col_w:.0f}" y1="28" x2="{2*col_w:.0f}" y2="{H-28}" stroke="{palette["divider"]}"/>

  <g text-anchor="middle" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif">
    <text x="{col_w/2:.0f}" y="70" font-size="34" font-weight="700" fill="{palette["number"]}">{total}</text>
    <text x="{col_w/2:.0f}" y="98" font-size="13" fill="{palette["label"]}">Total Contributions</text>
    <text x="{col_w/2:.0f}" y="116" font-size="11" fill="{palette["sub"]}">{total_range}</text>

    <circle cx="{ring_cx:.0f}" cy="{ring_cy}" r="{ring_r}" fill="none" stroke="{palette["ring_track"]}" stroke-width="4"/>
    <circle cx="{ring_cx:.0f}" cy="{ring_cy}" r="{ring_r}" fill="none" stroke="{palette["number"]}" stroke-width="4"
      stroke-linecap="round" stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{circumference*(1-frac):.1f}"
      transform="rotate(-90 {ring_cx:.0f} {ring_cy})"/>


    <g transform="translate(0, 12)">
      <text x="{1.5*col_w:.0f}" y="70" font-size="30" font-weight="700" fill="{palette["number"]}">{cur_len}</text>
      <text x="{1.5*col_w:.0f}" y="98" font-size="13" font-weight="600" fill="{palette["number"]}">Current Streak</text>
      <text x="{1.5*col_w:.0f}" y="116" font-size="11" fill="{palette["sub"]}">{cur_range}</text>
    </g>

    <text x="{2.5*col_w:.0f}" y="70" font-size="34" font-weight="700" fill="{palette["number"]}">{long_len}</text>
    <text x="{2.5*col_w:.0f}" y="98" font-size="13" fill="{palette["label"]}">Longest Streak</text>
    <text x="{2.5*col_w:.0f}" y="116" font-size="11" fill="{palette["sub"]}">{long_range}</text>
  </g>
</svg>'''


def main():
    days = fetch_days()
    stats = compute_stats(days)
    print(f"total={stats['total']} current={stats['current']} longest={stats['longest']}")
    for name, palette in PALETTES.items():
        svg = render(palette, stats)
        with open(palette["out"], "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{palette['out']}: {len(svg)} bytes ({name})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the profile SVG cards from live GitHub data.

Cards are generated locally so the profile does not depend on third-party
image services. Run:  python3 scripts/build_svgs.py
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

USER = "VPNmAsteRR"
ROOT = Path(__file__).resolve().parent.parent

BG = "#0d1117"
STROKE = "#7c3aed"
ACCENT = "#b366ff"
TEXT = "#c792ea"
MUTED = "#8b949e"
DIM = "#6e7681"
GREEN = "#56d364"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"

LEVEL_COLORS = ["#161b22", "#3c1f6b", "#6d34b8", "#9b5cff", "#c9a2ff"]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-svg-builder"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def load_contributions() -> dict[date, int]:
    html = fetch(f"https://github.com/users/{USER}/contributions")
    cells = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?id="contribution-day-component-(\d+)-(\d+)"',
        html,
    )
    tips = dict(
        re.findall(
            r'<tool-tip[^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>',
            html,
        )
    )
    days: dict[date, int] = {}
    for iso, col, row in cells:
        key = f"contribution-day-component-{col}-{row}"
        label = tips.get(key, "")
        if label.startswith("No contributions"):
            count = 0
        else:
            match = re.match(r"(\d+)", label)
            count = int(match.group(1)) if match else 0
        days[date.fromisoformat(iso)] = count
    return days


def streaks(days: dict[date, int]) -> tuple[int, int]:
    ordered = sorted(days)
    longest = current = 0
    prev: date | None = None
    for day in ordered:
        if days[day] > 0:
            current = current + 1 if prev == day - timedelta(days=1) else 1
            longest = max(longest, current)
        else:
            current = 0
        prev = day
    running = 0
    cursor = max(ordered) if ordered else date.today()
    while days.get(cursor, 0) > 0:
        running += 1
        cursor -= timedelta(days=1)
    return running, longest


def level(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def card(width: int, height: int, body: str) -> str:
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .h {{ font: 600 15px {SANS}; fill: {ACCENT}; }}
    .m {{ font: 400 13px {MONO}; fill: {MUTED}; }}
    .v {{ font: 600 14px {SANS}; fill: {TEXT}; }}
    .big {{ font: 800 30px {SANS}; fill: {TEXT}; }}
    .fade {{ opacity: 0; animation: fade .6s ease-out forwards; }}
    @keyframes fade {{ to {{ opacity: 1; }} }}
    @keyframes pop {{ 0% {{ transform: scale(.2); opacity: 0; }} 100% {{ transform: scale(1); opacity: 1; }} }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="20" fill="{BG}" stroke="{STROKE}"/>
{body}
</svg>
'''


def build_graph(days: dict[date, int]) -> str:
    width, height = 1200, 420
    cell, gap = 14, 4
    left, top = 96, 132
    ordered = sorted(days)
    first = ordered[0]
    # Align the first column with the weekday of the first day.
    offset = (first.weekday() + 1) % 7  # Sunday = 0
    weeks = (offset + len(ordered) + 6) // 7

    grid = []
    for index, day in enumerate(ordered):
        slot = offset + index
        col, row = divmod(slot, 7)
        x = left + col * (cell + gap)
        y = top + row * (cell + gap)
        count = days[day]
        label = f"{count} contributions on {day:%B} {day.day}"
        grid.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{LEVEL_COLORS[level(count)]}" class="fade" style="animation-delay:{(col * 0.006 + row * 0.004):.3f}s">'
            f"<title>{label}</title></rect>"
        )

    months = []
    seen = set()
    for index, day in enumerate(ordered):
        if day.day <= 7 and day.month not in seen:
            seen.add(day.month)
            slot = offset + index
            col = slot // 7
            x = left + col * (cell + gap)
            months.append(f'<text x="{x}" y="{top - 14}" class="m">{day:%b}</text>')

    weekdays = []
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = top + row * (cell + gap) + 11
        weekdays.append(f'<text x="52" y="{y}" class="m">{name}</text>')

    legend_x = width - 236
    legend_y = top + 7 * (cell + gap) + 26
    legend = [f'<text x="{legend_x - 44}" y="{legend_y + 11}" class="m">Less</text>']
    for i, color in enumerate(LEVEL_COLORS):
        legend.append(
            f'<rect x="{legend_x + i * 20}" y="{legend_y}" width="{cell}" height="{cell}" rx="3" fill="{color}"/>'
        )
    legend.append(f'<text x="{legend_x + 5 * 20 + 4}" y="{legend_y + 11}" class="m">More</text>')

    total = sum(days.values())
    body = f'''  <text x="40" y="54" class="h">~/contributions<span style="fill:{DIM}"> — last 365 days</span></text>
  <text x="{width - 40}" y="54" text-anchor="end" class="v">{total} contributions</text>
  <line x1="40" y1="76" x2="{width - 40}" y2="76" stroke="#21262d"/>
  <text x="40" y="104" class="m">$ git log --graph --all --oneline | wc -l</text>
  <text x="{left}" y="{top - 36}" class="m">  weeks: {weeks}   days: {len(ordered)}</text>
  {"".join(months)}
  {"".join(weekdays)}
  {"".join(grid)}
  {"".join(legend)}'''
    return card(width, height, body)


def build_stats(days: dict[date, int], user: dict, repos: list[dict]) -> str:
    width, height = 495, 195
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    current, longest = streaks(days)
    rows = [
        ("contributions", f"{sum(days.values())}"),
        ("repositories", f"{user.get('public_repos', 0)}"),
        ("stars earned", f"{stars}"),
        ("followers", f"{user.get('followers', 0)}"),
    ]
    body_rows = []
    for index, (label, value) in enumerate(rows):
        y = 86 + index * 26
        delay = 0.1 + index * 0.08
        body_rows.append(
            f'  <g class="fade" style="animation-delay:{delay:.2f}s">'
            f'<circle cx="44" cy="{y - 5}" r="4" fill="{ACCENT}"/>'
            f'<text x="62" y="{y}" class="v">{value} <tspan fill="{MUTED}" style="font-weight:400">{label}</tspan></text>'
            f"</g>"
        )

    ring_cx, ring_cy, ring_r = 408, 100, 46
    circumference = 2 * 3.141592653589793 * ring_r
    fraction = min(longest / 30, 1) if longest else 0
    dash = circumference * fraction

    body = f'''  <text x="40" y="44" class="h">~/stats</text>
  <text x="{width - 40}" y="44" text-anchor="end" class="m">$ whoami --stats</text>
  <line x1="40" y1="62" x2="{width - 40}" y2="62" stroke="#21262d"/>
  {"".join(body_rows)}
  <circle cx="{ring_cx}" cy="{ring_cy}" r="{ring_r}" fill="none" stroke="{ACCENT}" stroke-opacity="0.18" stroke-width="7"/>
  <circle cx="{ring_cx}" cy="{ring_cy}" r="{ring_r}" fill="none" stroke="{ACCENT}" stroke-width="7" stroke-linecap="round"
          stroke-dasharray="{dash:.2f} {circumference:.2f}" transform="rotate(-90 {ring_cx} {ring_cy})"
          opacity="0">
    <animate attributeName="stroke-dasharray" from="0 {circumference:.2f}" to="{dash:.2f} {circumference:.2f}" dur="1.2s" fill="freeze"/>
    <animate attributeName="opacity" from="0" to="1" dur="0.1s" fill="freeze"/>
  </circle>
  <text x="{ring_cx}" y="{ring_cy + 2}" text-anchor="middle" class="big">{current}</text>
  <text x="{ring_cx}" y="{ring_cy + 24}" text-anchor="middle" class="m">day streak</text>'''
    return card(width, height, body)


def build_streak(days: dict[date, int]) -> str:
    width, height = 495, 195
    current, longest = streaks(days)
    columns = [
        ("current streak", f"{current}d", "days in a row"),
        ("longest streak", f"{longest}d", "personal best"),
        ("total", f"{sum(days.values())}", "contributions"),
    ]
    body = f'''  <text x="40" y="44" class="h">~/streak</text>
  <text x="{width - 40}" y="44" text-anchor="end" class="m">$ cat streak.log</text>
  <line x1="40" y1="62" x2="{width - 40}" y2="62" stroke="#21262d"/>
  <g class="fade" style="animation-delay:.15s">
    <text x="40" y="112" class="m">streak</text>
    <text x="40" y="152" class="big" style="font-size:34px">{columns[0][1]}</text>
    <text x="40" y="174" class="m" style="font-size:11px">{columns[0][2]}</text>
  </g>
  <g class="fade" style="animation-delay:.3s">
    <text x="200" y="112" class="m">best</text>
    <text x="200" y="152" class="big" style="font-size:34px">{columns[1][1]}</text>
    <text x="200" y="174" class="m" style="font-size:11px">{columns[1][2]}</text>
  </g>
  <g class="fade" style="animation-delay:.45s">
    <text x="355" y="112" class="m">total</text>
    <text x="355" y="152" class="big" style="font-size:34px">{columns[2][1]}</text>
    <text x="355" y="174" class="m" style="font-size:11px">{columns[2][2]}</text>
  </g>
  <line x1="180" y1="96" x2="180" y2="168" stroke="#21262d"/>
  <line x1="335" y1="96" x2="335" y2="168" stroke="#21262d"/>'''
    return card(width, height, body)


def build_pin(index: int, repo: dict, blurb: str) -> str:
    width, height = 400, 150
    name = repo["name"]
    language = repo.get("language") or "no code yet"
    stars = repo.get("stargazers_count", 0)
    size = repo.get("size", 0)

    if len(blurb) > 62:
        cut = blurb.rfind(" ", 0, 62)
        blurb = f"{blurb[:cut]}\n{blurb[cut + 1:]}"
    lines = blurb.split("\n")
    description = "".join(
        f'<text x="24" y="{74 + i * 19}" class="m" style="font-size:12px">{line}</text>'
        for i, line in enumerate(lines[:2])
    )

    body = f'''  <text x="24" y="42" class="h" style="font-size:16px">{name}</text>
  <text x="{width - 24}" y="42" text-anchor="end" class="m" style="font-size:11px">~/repos/{index:02d}</text>
  <line x1="24" y1="54" x2="{width - 24}" y2="54" stroke="#21262d"/>
{description}
  <circle cx="30" cy="122" r="5" fill="{ACCENT}"/>
  <text x="42" y="126" class="v" style="font-size:12px">{language}</text>
  <text x="{width - 24}" y="126" text-anchor="end" class="m" style="font-size:11px">★ {stars}   ·   {size} KB   ·   open ↗</text>'''
    return card(width, height, body)


def main() -> None:
    days = load_contributions()
    user = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100"))

    (ROOT / "graph.svg").write_text(build_graph(days), encoding="utf-8")
    (ROOT / "stats.svg").write_text(build_stats(days, user, repos), encoding="utf-8")
    (ROOT / "streak.svg").write_text(build_streak(days), encoding="utf-8")

    blurbs = {
        "time-clicker": "Браузерная игра-кликер на чистом HTML и JavaScript.",
        "TeleGBot": "Telegram-бот на Python — репозиторий в работе.",
    }
    pins = [r for r in repos if r["name"] in blurbs][:2]
    for position, repo in enumerate(pins, start=1):
        svg = build_pin(position, repo, blurbs[repo["name"]])
        (ROOT / f"pin{position}.svg").write_text(svg, encoding="utf-8")

    language_counts = Counter(r.get("language") for r in repos if r.get("language"))
    print("days:", len(days), "| total:", sum(days.values()), "| streak:", streaks(days))
    print("repos:", [r["name"] for r in repos], "| languages:", dict(language_counts))


if __name__ == "__main__":
    main()

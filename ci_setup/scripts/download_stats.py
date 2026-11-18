"""
Append today's GitHub release download counts to stats/downloads.csv and redraw
stats/downloads.svg (total downloads over time). Standard library only.

Env: REPO=owner/name, GH_TOKEN (optional but avoids rate limits).
"""
import csv
import datetime as dt
import json
import os
import pathlib
import urllib.request

REPO = os.environ.get("REPO", "ryusei-inamori/FusedMaker")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = pathlib.Path(__file__).resolve().parents[2] / "stats"
CSV = OUT / "downloads.csv"
SVG = OUT / "downloads.svg"
FIELDS = ["date", "tag", "asset", "downloads"]


def api(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_counts():
    rows, page = [], 1
    while True:
        releases = api(f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}")
        if not releases:
            break
        for rel in releases:
            for a in rel.get("assets", []):
                rows.append((rel["tag_name"], a["name"], int(a["download_count"])))
        page += 1
    return rows


def update_csv(today, counts):
    OUT.mkdir(exist_ok=True)
    old = []
    if CSV.exists():
        with open(CSV, newline="", encoding="utf-8") as f:
            old = [r for r in csv.DictReader(f) if r["date"] != today]   # one snapshot per day
    new = [{"date": today, "tag": t, "asset": n, "downloads": c} for t, n, c in counts]
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(old + new)
    return old + new


def daily_totals(rows, only_exe=True):
    tot = {}
    for r in rows:
        if only_exe and not r["asset"].lower().endswith(".exe"):
            continue
        tot[r["date"]] = tot.get(r["date"], 0) + int(r["downloads"])
    return sorted(tot.items())


def draw_svg(series):
    W, H, L, R, T, B = 720, 300, 60, 45, 40, 45
    if not series:
        series = [(dt.date.today().isoformat(), 0)]
    ymax = max(1, max(v for _, v in series))
    raw = ymax / 4
    mag = 10 ** max(0, len(str(int(raw))) - 1)
    nice = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    ytop = int(4 * nice)
    n = len(series)
    x = lambda i: L + (W - L - R) * (i / (n - 1) if n > 1 else 0.5)
    y = lambda v: T + (H - T - B) * (1 - v / ytop)
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(series))
    grid = "".join(
        f'<line x1="{L}" y1="{y(ytop * k / 4):.1f}" x2="{W - R}" y2="{y(ytop * k / 4):.1f}" stroke="#e5e7eb"/>'
        f'<text x="{L - 8}" y="{y(ytop * k / 4) + 4:.1f}" font-size="11" text-anchor="end" fill="#6b7280">{ytop * k // 4}</text>'
        for k in range(5))
    labels = ""
    for i in sorted({0, n - 1, n // 2}):
        anchor = "start" if i == 0 and n > 1 else ("end" if i == n - 1 and n > 1 else "middle")
        labels += (f'<text x="{x(i):.1f}" y="{H - B + 18}" font-size="11" text-anchor="{anchor}" '
                   f'fill="#6b7280">{series[i][0]}</text>')
    last = series[-1][1]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif">'
            f'<rect width="{W}" height="{H}" fill="white"/>'
            f'<text x="{L}" y="24" font-size="15" font-weight="600" fill="#111827">'
            f'FusedAuto.exe downloads (cumulative): {last}</text>{grid}'
            f'<polyline points="{pts}" fill="none" stroke="#2563eb" stroke-width="2.5"/>'
            f'{labels}</svg>\n')


def main():
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    counts = fetch_counts()
    rows = update_csv(today, counts)
    SVG.write_text(draw_svg(daily_totals(rows)), encoding="utf-8")
    total = sum(c for t, n, c in counts if n.lower().endswith(".exe"))
    print(f"{today}: {len(counts)} assets, FusedAuto.exe downloads = {total}")


if __name__ == "__main__":
    main()

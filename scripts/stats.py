#!/usr/bin/env python3
"""Generate themed GitHub stats SVGs into assets/ (no third-party services).

Runs in GitHub Actions with GITHUB_TOKEN. Pass --sample to render with fake
data for local previewing.
"""
import json, os, sys, urllib.request
from datetime import date
from html import escape

USER = os.environ.get("GH_USER", "CryptoCaleb")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

BG, BORDER, TITLE, TEXT, MUTED = "#0f0c29", "#302b63", "#a78bfa", "#e6e1ff", "#8a84b8"
PINK, GREEN = "#ff4d8d", "#8bf5a8"
FONT = "font-family=\"'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif\""

QUERY = """
query($login:String!){ user(login:$login){
  followers{totalCount}
  repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){
    totalCount
    nodes{ stargazerCount
      languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}} } }
  contributionsCollection{
    totalCommitContributions totalPullRequestContributions totalIssueContributions
    contributionCalendar{ totalContributions weeks{contributionDays{date contributionCount}} } } } }
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def sample():
    import random
    random.seed(4)
    days = [{"date": f"2026-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}",
             "contributionCount": max(0, int(random.gauss(3, 3)))} for i in range(365)]
    langs = [("TypeScript", "#3178c6", 9e5), ("JavaScript", "#f1e05a", 6e5),
             ("Python", "#3572A5", 3e5), ("C++", "#f34b7d", 2e5), ("PHP", "#4F5D95", 1e5)]
    return {
        "followers": {"totalCount": 12},
        "repositories": {"totalCount": 5, "nodes": [
            {"stargazerCount": 3, "languages": {"edges": [
                {"size": s, "node": {"name": n, "color": c}} for n, c, s in langs]}}]},
        "contributionsCollection": {
            "totalCommitContributions": 412, "totalPullRequestContributions": 18,
            "totalIssueContributions": 7,
            "contributionCalendar": {"totalContributions": sum(d["contributionCount"] for d in days),
                                     "weeks": [{"contributionDays": days[i:i + 7]} for i in range(0, 365, 7)]}},
    }


def frame(w, h, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>
  .fade{{opacity:0;animation:in .6s ease-out forwards}}
  @keyframes in{{to{{opacity:1}}}}
  .grow{{transform-origin:left;transform:scaleX(0);animation:g 1s ease-out forwards}}
  @keyframes g{{to{{transform:scaleX(1)}}}}
  .draw{{stroke-dasharray:4000;stroke-dashoffset:4000;animation:d 2.2s ease-out forwards}}
  @keyframes d{{to{{stroke-dashoffset:0}}}}
</style>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="14" fill="{BG}" stroke="{BORDER}"/>
<text x="25" y="36" {FONT} font-size="18" font-weight="700" fill="{TITLE}">{escape(title)}</text>
{body}
</svg>"""


def stats_card(u):
    c = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    rows = [("★", "Total stars", stars),
            ("⎇", "Commits (past year)", c["totalCommitContributions"]),
            ("⇄", "Pull requests", c["totalPullRequestContributions"]),
            ("!", "Issues", c["totalIssueContributions"]),
            ("▣", "Public repos", u["repositories"]["totalCount"]),
            ("♥", "Followers", u["followers"]["totalCount"])]
    body = []
    for i, (icon, label, val) in enumerate(rows):
        y = 70 + i * 24
        body.append(
            f'<g class="fade" style="animation-delay:{i*120}ms">'
            f'<circle cx="31" cy="{y-5}" r="4" fill="{PINK if i % 2 == 0 else GREEN}"/>'
            f'<text x="48" y="{y}" {FONT} font-size="14" fill="{TEXT}">{label}</text>'
            f'<text x="290" y="{y}" {FONT} font-size="14" font-weight="700" fill="{TEXT}" text-anchor="end">{val:,}</text></g>')
    total = c["contributionCalendar"]["totalContributions"]
    cx, cy, r = 385, 115, 48
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="7"/>')
    body.append(f'<circle class="draw" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TITLE}" stroke-width="7" '
                f'stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>')
    body.append(f'<text x="{cx}" y="{cy+2}" {FONT} font-size="22" font-weight="700" fill="{GREEN}" text-anchor="middle">{total:,}</text>')
    body.append(f'<text x="{cx}" y="{cy+20}" {FONT} font-size="10" fill="{MUTED}" text-anchor="middle">contributions</text>')
    return frame(470, 215, f"{USER}'s GitHub Stats", "\n".join(body))


def langs_card(u):
    totals = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            size, col = totals.get(n, (0, e["node"]["color"] or MUTED))
            totals[n] = (size + e["size"], col)
    top = sorted(totals.items(), key=lambda kv: -kv[1][0])[:6]
    whole = sum(s for _, (s, _) in top) or 1
    body, x = [], 25
    for i, (name, (size, col)) in enumerate(top):
        w = 250 * size / whole
        body.append(f'<rect class="grow" style="animation-delay:{i*80}ms" x="{x:.1f}" y="55" width="{w:.1f}" height="10" fill="{col}"/>')
        x += w
    body.insert(0, f'<clipPath id="bar"><rect x="25" y="55" width="250" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    body.append("</g>")
    for i, (name, (size, col)) in enumerate(top):
        cx, cy = 25 + (i % 2) * 130, 95 + (i // 2) * 26
        body.append(
            f'<g class="fade" style="animation-delay:{300+i*100}ms">'
            f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{col}"/>'
            f'<text x="{cx+16}" y="{cy}" {FONT} font-size="12" fill="{TEXT}">{escape(name)} '
            f'<tspan fill="{MUTED}">{100*size/whole:.1f}%</tspan></text></g>')
    return frame(300, 215, "Most Used Languages", "\n".join(body))


def activity_card(u):
    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]
            for d in w["contributionDays"]][-60:]
    counts = [d["contributionCount"] for d in days]
    W, H, L, T, B = 800, 260, 50, 60, 220
    peak = max(max(counts), 1)
    step = (W - L - 25) / max(len(counts) - 1, 1)
    pts = [(L + i * step, B - (B - T) * c / peak) for i, c in enumerate(counts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{L},{B} {line} {pts[-1][0]:.1f},{B}"
    grid = "".join(
        f'<line x1="{L}" x2="{W-25}" y1="{B-(B-T)*k/4:.1f}" y2="{B-(B-T)*k/4:.1f}" stroke="{BORDER}" stroke-dasharray="3 4"/>'
        f'<text x="{L-10}" y="{B-(B-T)*k/4+4:.1f}" {FONT} font-size="10" fill="{MUTED}" text-anchor="end">{round(peak*k/4)}</text>'
        for k in range(5))
    labels = "".join(
        f'<text x="{pts[i][0]:.1f}" y="{B+20}" {FONT} font-size="10" fill="{MUTED}" text-anchor="middle">{days[i]["date"][5:]}</text>'
        for i in range(0, len(days), 10))
    dots = "".join(f'<circle class="fade" style="animation-delay:{1500+i*10}ms" cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{GREEN}"/>'
                   for i, (x, y) in enumerate(pts))
    body = f"""<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{TITLE}" stop-opacity=".45"/><stop offset="1" stop-color="{TITLE}" stop-opacity="0"/></linearGradient></defs>
{grid}{labels}
<polygon class="fade" style="animation-delay:900ms" points="{area}" fill="url(#ar)"/>
<polyline class="draw" points="{line}" fill="none" stroke="{PINK}" stroke-width="2.5" stroke-linejoin="round"/>
{dots}
<text x="{W-25}" y="36" {FONT} font-size="11" fill="{MUTED}" text-anchor="end">last 60 days · updated {date.today():%b %d, %Y}</text>"""
    return frame(W, H, "Contribution Activity", body)


def main():
    u = sample() if "--sample" in sys.argv else fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, svg in [("stats.svg", stats_card(u)), ("langs.svg", langs_card(u)),
                      ("activity.svg", activity_card(u))]:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()

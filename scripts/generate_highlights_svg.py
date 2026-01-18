import os
import datetime as dt
import requests

GH_TOKEN = os.environ.get("GH_TOKEN")
GH_USER = os.environ.get("GH_USER", "jaafar-harabi")

if not GH_TOKEN:
    raise SystemExit("Missing GH_TOKEN env var")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})

# Pull current assets numbers from APIs (same logic as impact card)
repos = []
page = 1
while True:
    r = session.get(f"https://api.github.com/users/{GH_USER}/repos", params={"per_page": 100, "page": page}, timeout=30)
    r.raise_for_status()
    batch = r.json()
    if not batch:
        break
    repos.extend(batch)
    page += 1

stars = sum(int(x.get("stargazers_count", 0)) for x in repos)
forks = sum(int(x.get("forks_count", 0)) for x in repos)

pr_q = f"type:pr author:{GH_USER} is:merged"
issue_q = f"type:issue author:{GH_USER}"
pr_count = session.get("https://api.github.com/search/issues", params={"q": pr_q}, timeout=30).json().get("total_count", 0)
issue_count = session.get("https://api.github.com/search/issues", params={"q": issue_q}, timeout=30).json().get("total_count", 0)

# Simple milestone logic (edit thresholds as you like)
def badge(label, ok):
    return f"✅ {label}" if ok else f"⬜ {label}"

highlights = [
    badge("100+ stars earned", stars >= 100),
    badge("25+ forks across repos", forks >= 25),
    badge("100+ PRs merged", pr_count >= 100),
    badge("100+ issues opened", issue_count >= 100),
]

# Show 4 lines
line1, line2, line3, line4 = (highlights + [""]*4)[:4]

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="190" role="img" aria-label="Highlights">
  <rect width="860" height="190" rx="16" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">Achievements & Highlights</text>

  <text x="30" y="88" fill="#c9d1d9" font-size="16" font-family="Verdana">{line1}</text>
  <text x="30" y="116" fill="#c9d1d9" font-size="16" font-family="Verdana">{line2}</text>
  <text x="30" y="144" fill="#c9d1d9" font-size="16" font-family="Verdana">{line3}</text>
  <text x="30" y="172" fill="#c9d1d9" font-size="16" font-family="Verdana">{line4}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-highlights.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-highlights.svg")

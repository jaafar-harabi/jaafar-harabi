import os
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

# Helper to paginate REST endpoints
def paginate(url, params=None):
    page = 1
    items = []
    while True:
        p = dict(params or {})
        p.update({"per_page": 100, "page": page})
        r = session.get(url, params=p, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        items.extend(batch)
        page += 1
    return items

# Repos (public)
repos = paginate(f"https://api.github.com/users/{GH_USER}/repos", params={"sort": "updated"})
public_repos = len(repos)
stars = sum(int(x.get("stargazers_count", 0)) for x in repos)
forks = sum(int(x.get("forks_count", 0)) for x in repos)

# Merged PRs (all-time) + Issues opened (all-time)
# We use GitHub Search API (reliable). Note: search results cap at 1000.
# For most profiles, this is enough; for huge profiles, we can add date-chunking later.
pr_q = f"type:pr author:{GH_USER} is:merged"
issue_q = f"type:issue author:{GH_USER}"

pr_count = session.get("https://api.github.com/search/issues", params={"q": pr_q}, timeout=30).json().get("total_count", 0)
issue_count = session.get("https://api.github.com/search/issues", params={"q": issue_q}, timeout=30).json().get("total_count", 0)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="180" role="img" aria-label="All-time impact">
  <rect width="860" height="180" rx="16" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">All-time Impact</text>

  <text x="30" y="86" fill="#c9d1d9" font-size="16" font-family="Verdana">Public repos:</text>
  <text x="160" y="86" fill="#58a6ff" font-size="18" font-family="Verdana">{public_repos}</text>

  <text x="260" y="86" fill="#c9d1d9" font-size="16" font-family="Verdana">Stars:</text>
  <text x="330" y="86" fill="#3fb950" font-size="18" font-family="Verdana">{stars}</text>

  <text x="420" y="86" fill="#c9d1d9" font-size="16" font-family="Verdana">Forks:</text>
  <text x="500" y="86" fill="#f78166" font-size="18" font-family="Verdana">{forks}</text>

  <text x="30" y="124" fill="#c9d1d9" font-size="16" font-family="Verdana">Merged PRs:</text>
  <text x="160" y="124" fill="#58a6ff" font-size="18" font-family="Verdana">{pr_count}</text>

  <text x="260" y="124" fill="#c9d1d9" font-size="16" font-family="Verdana">Issues opened:</text>
  <text x="420" y="124" fill="#58a6ff" font-size="18" font-family="Verdana">{issue_count}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-impact-alltime.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-impact-alltime.svg")

import os
import requests

GH_TOKEN = os.environ.get("GH_TOKEN")
GH_USER = os.environ.get("GH_USER", "jaafar-harabi")

if not GH_TOKEN:
    raise SystemExit("Missing GH_TOKEN env var")

def xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})

# repos
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

# merged PRs + issues opened
pr_q = f"type:pr author:{GH_USER} is:merged"
issue_q = f"type:issue author:{GH_USER}"

pr_count = session.get("https://api.github.com/search/issues", params={"q": pr_q}, timeout=30).json().get("total_count", 0)
issue_count = session.get("https://api.github.com/search/issues", params={"q": issue_q}, timeout=30).json().get("total_count", 0)

def mark(ok: bool) -> str:
    return "✅" if ok else "⬜"

lines = [
    f"{mark(stars >= 100)} ⭐ Stars earned: {stars}",
    f"{mark(forks >= 25)} 🍴 Forks across repos: {forks}",
    f"{mark(pr_count >= 100)} 🔀 Merged PRs: {pr_count}",
    f"{mark(issue_count >= 100)} 🧩 Issues opened: {issue_count}",
]

lines = [xml_escape(x) for x in lines]

title = xml_escape("🏅 Highlights")
subtitle = xml_escape("Milestones based on your public GitHub activity")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="210" role="img" aria-label="GitHub highlights">
  <defs>
    <linearGradient id="bg3" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>

  <rect width="860" height="210" rx="18" fill="url(#bg3)" stroke="#30363d"/>
  <text x="34" y="52" fill="#c9d1d9" font-size="24" font-family="Verdana">{title}</text>
  <text x="34" y="78" fill="#8b949e" font-size="13" font-family="Verdana">{subtitle}</text>

  <rect x="34" y="96" width="792" height="96" rx="14" fill="#0b0f14" stroke="#21262d"/>

  <text x="56" y="126" fill="#c9d1d9" font-size="16" font-family="Verdana">{lines[0]}</text>
  <text x="56" y="150" fill="#c9d1d9" font-size="16" font-family="Verdana">{lines[1]}</text>
  <text x="56" y="174" fill="#c9d1d9" font-size="16" font-family="Verdana">{lines[2]}</text>
  <text x="56" y="198" fill="#c9d1d9" font-size="16" font-family="Verdana">{lines[3]}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-highlights.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-highlights.svg")

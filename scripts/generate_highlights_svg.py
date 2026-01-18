import os
import requests

# =========================
# Config
# =========================
GH_TOKEN = os.environ.get("GH_TOKEN")
GH_USER = os.environ.get("GH_USER", "jaafar-harabi")

if not GH_TOKEN:
    raise SystemExit("Missing GH_TOKEN environment variable")

# =========================
# Helpers
# =========================
def xml_escape(s: str) -> str:
    """Escape text for safe XML/SVG rendering."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )

def badge(label: str, ok: bool) -> str:
    return f"[OK] {label}" if ok else f"[ ]  {label}"

# =========================
# GitHub API session
# =========================
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})

# =========================
# Fetch repos
# =========================
repos = []
page = 1
while True:
    r = session.get(
        f"https://api.github.com/users/{GH_USER}/repos",
        params={"per_page": 100, "page": page},
        timeout=30,
    )
    r.raise_for_status()
    batch = r.json()
    if not batch:
        break
    repos.extend(batch)
    page += 1

stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
forks = sum(int(r.get("forks_count", 0)) for r in repos)

# =========================
# PRs and issues (search API)
# =========================
pr_q = f"type:pr author:{GH_USER} is:merged"
issue_q = f"type:issue author:{GH_USER}"

pr_count = session.get(
    "https://api.github.com/search/issues",
    params={"q": pr_q},
    timeout=30,
).json().get("total_count", 0)

issue_count = session.get(
    "https://api.github.com/search/issues",
    params={"q": issue_q},
    timeout=30,
).json().get("total_count", 0)

# =========================
# Achievements logic
# =========================
highlights = [
    badge("100+ stars earned across repositories", stars >= 100),
    badge("25+ forks across repositories", forks >= 25),
    badge("100+ merged pull requests", pr_count >= 100),
    badge("100+ issues opened", issue_count >= 100),
]

# Escape text
lines = [xml_escape(h) for h in highlights]

# =========================
# SVG Output
# =========================
title = xml_escape("Achievements and Highlights")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="200" role="img" aria-label="GitHub achievements">
  <rect width="860" height="200" rx="16" fill="#0d1117" stroke="#30363d"/>

  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">
    {title}
  </text>

  <text x="30" y="88" fill="#c9d1d9" font-size="16" font-family="Verdana">
    {lines[0]}
  </text>

  <text x="30" y="116" fill="#c9d1d9" font-size="16" font-family="Verdana">
    {lines[1]}
  </text>

  <text x="30" y="144" fill="#c9d1d9" font-size="16" font-family="Verdana">
    {lines[2]}
  </text>

  <text x="30" y="172" fill="#c9d1d9" font-size="16" font-family="Verdana">
    {lines[3]}
  </text>
</svg>
"""

# =========================
# Write file
# =========================
os.makedirs("assets", exist_ok=True)
out_path = "assets/github-highlights.svg"

with open(out_path, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Wrote {out_path}")

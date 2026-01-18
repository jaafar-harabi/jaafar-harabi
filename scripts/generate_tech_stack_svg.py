import os
import requests
from collections import Counter

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

repos = paginate(f"https://api.github.com/users/{GH_USER}/repos", params={"sort": "updated"})

lang_counter = Counter()
for repo in repos:
    if repo.get("fork"):
        continue
    lang_url = repo.get("languages_url")
    if not lang_url:
        continue
    r = session.get(lang_url, timeout=30)
    if r.status_code != 200:
        continue
    for lang, bytes_ in r.json().items():
        lang_counter[lang] += int(bytes_)

total_bytes = sum(lang_counter.values()) or 1
top = lang_counter.most_common(6)

# Build lines like: "HCL 35% · Python 22% ..."
parts = []
for lang, b in top:
    pct = round((b / total_bytes) * 100)
    parts.append(f"{lang} {pct}%")
top_text = " · ".join(parts) if parts else "-"

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="160" role="img" aria-label="Tech stack">
  <rect width="860" height="160" rx="16" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">Top Technologies</text>

  <text x="30" y="92" fill="#c9d1d9" font-size="16" font-family="Verdana">{top_text}</text>

  <text x="30" y="132" fill="#8b949e" font-size="12" font-family="Verdana">Based on language bytes across non-fork repos</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-tech.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-tech.svg")

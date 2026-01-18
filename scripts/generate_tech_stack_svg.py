import os
import re
import requests
from collections import Counter

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

# --- languages (bytes) ---
lang_counter = Counter()
# --- devops/cloud tool signals ---
tool_counter = Counter()

# keywords -> canonical tool name
TOOL_MAP = {
    r"\bterraform\b": "Terraform",
    r"\bterragrunt\b": "Terragrunt",
    r"\bkubernetes\b|\bk8s\b": "Kubernetes",
    r"\bhelm\b": "Helm",
    r"\bargocd\b|\bargo cd\b": "ArgoCD",
    r"\bgithub actions\b|\bactions\b": "GitHub Actions",
    r"\bjenkins\b": "Jenkins",
    r"\bgitlab ci\b|\bgitlab\b": "GitLab CI",
    r"\bansible\b": "Ansible",
    r"\bprometheus\b": "Prometheus",
    r"\bgrafana\b": "Grafana",
    r"\belk\b|\belasticsearch\b|\blogstash\b|\bkibana\b": "ELK",
    r"\baws\b|\bec2\b|\beks\b|\biam\b|\bvpc\b|\bs3\b": "AWS",
    r"\bazure\b": "Azure",
    r"\bgcp\b": "GCP",
    r"\bdocker\b": "Docker",
    r"\bvault\b": "Vault",
    r"\btrivy\b": "Trivy",
    r"\bsonarqube\b": "SonarQube",
    r"\bowasp\b|\bzap\b": "OWASP ZAP",
}

def detect_tools(text: str):
    t = (text or "").lower()
    for pattern, name in TOOL_MAP.items():
        if re.search(pattern, t):
            tool_counter[name] += 1

for repo in repos:
    if repo.get("fork"):
        continue

    # Detect tools from name/description
    detect_tools(repo.get("name", ""))
    detect_tools(repo.get("description", ""))

    # Detect tools from topics (requires preview header sometimes, but generally works)
    topics = repo.get("topics", []) or []
    for topic in topics:
        detect_tools(topic)

    # Languages bytes
    lang_url = repo.get("languages_url")
    if lang_url:
        lr = session.get(lang_url, timeout=30)
        if lr.status_code == 200:
            for k, v in lr.json().items():
                lang_counter[k] += int(v)

# Top languages (3)
top_langs = [k for k, _ in lang_counter.most_common(3)]
langs_text = " · ".join(top_langs) if top_langs else "-"

# Top tools/platforms (6)
top_tools = [k for k, _ in tool_counter.most_common(6)]
tools_text = " · ".join(top_tools) if top_tools else "-"

title = xml_escape("Cloud and DevOps Tech Stack")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="180" role="img" aria-label="Cloud DevOps tech stack">
  <rect width="860" height="180" rx="16" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">{title}</text>

  <text x="30" y="92" fill="#c9d1d9" font-size="16" font-family="Verdana">Top languages:</text>
  <text x="170" y="92" fill="#58a6ff" font-size="16" font-family="Verdana">{xml_escape(langs_text)}</text>

  <text x="30" y="130" fill="#c9d1d9" font-size="16" font-family="Verdana">Top tools/platforms:</text>
  <text x="210" y="130" fill="#3fb950" font-size="16" font-family="Verdana">{xml_escape(tools_text)}</text>

  <text x="30" y="160" fill="#8b949e" font-size="12" font-family="Verdana">Based on repo topics, names, descriptions, and language bytes</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-tech.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-tech.svg")

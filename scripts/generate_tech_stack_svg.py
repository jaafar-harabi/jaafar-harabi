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

TOOL_MAP = {
    r"\bterraform\b|\bhcl\b": "Terraform",
    r"\bterragrunt\b": "Terragrunt",
    r"\bkubernetes\b|\bk8s\b|\bek[s]?\b": "Kubernetes",
    r"\bhelm\b": "Helm",
    r"\bargocd\b|\bargo\s*cd\b": "ArgoCD",
    r"\bflux\b|\bfluxcd\b": "FluxCD",
    r"\bdocker\b": "Docker",
    r"\baws\b|\bec2\b|\bvpc\b|\beks\b|\becr\b|\bs3\b|\biam\b|\bcloudwatch\b": "AWS",
    r"\bazure\b": "Azure",
    r"\bgcp\b": "GCP",
    r"\bgithub\s*actions\b|\bgha\b": "GitHub Actions",
    r"\bjenkins\b": "Jenkins",
    r"\bansible\b": "Ansible",
    r"\bprometheus\b": "Prometheus",
    r"\bgrafana\b": "Grafana",
    r"\belk\b|\belasticsearch\b|\blogstash\b|\bkibana\b": "ELK",
    r"\bopentelemetry\b|\botel\b": "OpenTelemetry",
    r"\bvault\b": "Vault",
    r"\btrivy\b": "Trivy",
    r"\bsonarqube\b": "SonarQube",
}

def detect(text: str, counter: Counter):
    t = (text or "").lower()
    for pattern, name in TOOL_MAP.items():
        if re.search(pattern, t):
            counter[name] += 1

repos = paginate(f"https://api.github.com/users/{GH_USER}/repos", params={"sort": "updated"})
counter = Counter()

for repo in repos:
    if repo.get("fork"):
        continue
    detect(repo.get("name", ""), counter)
    detect(repo.get("description", ""), counter)
    for topic in (repo.get("topics", []) or []):
        detect(topic, counter)

top = [k for k, _ in counter.most_common(10)]
if not top:
    top = ["Terraform", "Kubernetes", "AWS", "GitHub Actions", "Helm", "ArgoCD", "Prometheus", "Grafana"]

primary = " · ".join(top[:8])
secondary = " · ".join(top[8:10]) if len(top) > 8 else ""

title = xml_escape("🧰 DevOps / Cloud Tech Focus")
subtitle = xml_escape("Detected from repository topics and descriptions")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="190" role="img" aria-label="DevOps cloud tools">
  <defs>
    <linearGradient id="bg2" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>

  <rect width="860" height="190" rx="18" fill="url(#bg2)" stroke="#30363d"/>
  <text x="34" y="52" fill="#c9d1d9" font-size="24" font-family="Verdana">{title}</text>
  <text x="34" y="78" fill="#8b949e" font-size="13" font-family="Verdana">{subtitle}</text>

  <rect x="34" y="96" width="792" height="68" rx="14" fill="#0b0f14" stroke="#21262d"/>

  <text x="56" y="124" fill="#3fb950" font-size="16" font-family="Verdana">Primary:</text>
  <text x="140" y="124" fill="#c9d1d9" font-size="16" font-family="Verdana">{xml_escape(primary)}</text>
"""

if secondary:
    svg += f"""
  <text x="56" y="150" fill="#58a6ff" font-size="16" font-family="Verdana">Also:</text>
  <text x="120" y="150" fill="#c9d1d9" font-size="16" font-family="Verdana">{xml_escape(secondary)}</text>
"""

svg += """
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-tech.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-tech.svg")

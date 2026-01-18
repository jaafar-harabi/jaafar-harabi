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

# DevOps/Cloud tool detection rules
# (pattern -> canonical tool name)
TOOL_MAP = {
    r"\bterraform\b|\bhcl\b": "Terraform",
    r"\bterragrunt\b": "Terragrunt",
    r"\bkubernetes\b|\bk8s\b|\bek[s]?\b": "Kubernetes",
    r"\bhelm\b": "Helm",
    r"\bargocd\b|\bargo\s*cd\b": "ArgoCD",
    r"\bflux\b|\bfluxcd\b": "FluxCD",
    r"\bdocker\b": "Docker",
    r"\bcontainerd\b": "containerd",
    r"\baws\b|\bec2\b|\bvpc\b|\beks\b|\becr\b|\bs3\b|\biam\b|\bcloudwatch\b": "AWS",
    r"\bazure\b|\baz-900\b": "Azure",
    r"\bgcp\b": "GCP",
    r"\bgithub\s*actions\b|\bgha\b": "GitHub Actions",
    r"\bjenkins\b": "Jenkins",
    r"\bgitlab\s*ci\b": "GitLab CI",
    r"\bansible\b": "Ansible",
    r"\bpacker\b": "Packer",
    r"\bvault\b|\bhashicorp\s*vault\b": "Vault",
    r"\bsecrets\s*manager\b|\bparameter\s*store\b": "Secrets Manager / SSM",
    r"\bprometheus\b": "Prometheus",
    r"\bgrafana\b": "Grafana",
    r"\belk\b|\belasticsearch\b|\blogstash\b|\bkibana\b": "ELK",
    r"\bopentelemetry\b|\botel\b": "OpenTelemetry",
    r"\bdatadog\b": "Datadog",
    r"\bnew\s*relic\b": "New Relic",
    r"\bsonarqube\b": "SonarQube",
    r"\btrivy\b": "Trivy",
    r"\bsnyk\b": "Snyk",
    r"\bowasp\b|\bzap\b": "OWASP ZAP",
    r"\bterraform\s*cloud\b|\btfe\b": "Terraform Cloud",
    r"\bistio\b": "Istio",
    r"\blinkerd\b": "Linkerd",
    r"\bnginx\b|\bingress\b": "Ingress / NGINX",
    r"\bpostgres\b|\bpostgresql\b": "PostgreSQL",
    r"\brds\b": "AWS RDS",
    r"\brabbitmq\b": "RabbitMQ",
    r"\bkafka\b": "Kafka",
}

def detect_tools(text: str, counter: Counter):
    t = (text or "").lower()
    for pattern, name in TOOL_MAP.items():
        if re.search(pattern, t):
            counter[name] += 1

repos = paginate(f"https://api.github.com/users/{GH_USER}/repos", params={"sort": "updated"})

tool_counter = Counter()

for repo in repos:
    if repo.get("fork"):
        continue

    # name + description
    detect_tools(repo.get("name", ""), tool_counter)
    detect_tools(repo.get("description", ""), tool_counter)

    # topics
    topics = repo.get("topics", []) or []
    for topic in topics:
        detect_tools(topic, tool_counter)

# If detection finds nothing (rare), show a default
if not tool_counter:
    top_tools = ["Terraform", "Kubernetes", "AWS", "GitHub Actions", "Prometheus", "Grafana"]
    also_used = []
else:
    top_tools = [k for k, _ in tool_counter.most_common(8)]
    also_used = [k for k, _ in tool_counter.most_common(14)][8:14]

top_line = " · ".join(top_tools)
also_line = " · ".join(also_used) if also_used else ""

title = xml_escape("DevOps and Cloud Technology Focus")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="185" role="img" aria-label="DevOps and Cloud tech stack">
  <rect width="860" height="185" rx="16" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">{title}</text>

  <text x="30" y="92" fill="#c9d1d9" font-size="16" font-family="Verdana">Primary tools:</text>
  <text x="160" y="92" fill="#3fb950" font-size="16" font-family="Verdana">{xml_escape(top_line)}</text>
"""

if also_line:
    svg += f"""
  <text x="30" y="128" fill="#c9d1d9" font-size="16" font-family="Verdana">Also used:</text>
  <text x="130" y="128" fill="#58a6ff" font-size="16" font-family="Verdana">{xml_escape(also_line)}</text>
"""

svg += """
  <text x="30" y="165" fill="#8b949e" font-size="12" font-family="Verdana">Derived from repository topics, names, and descriptions</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-tech.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-tech.svg")

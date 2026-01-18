import os
import datetime as dt
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

def gql(query: str, variables: dict):
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {GH_TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    j = r.json()
    if "errors" in j:
        raise SystemExit(f"GraphQL errors: {j['errors']}")
    return j["data"]

# createdAt
q_user = """query($login:String!) { user(login:$login) { createdAt } }"""
created_at = gql(q_user, {"login": GH_USER})["user"]["createdAt"]
created_dt = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))

# all-time contributions computed per-year
q_total = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar { totalContributions }
    }
  }
}
"""
now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

total_all_time = 0
y = created_dt.year
while True:
    start = dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(y + 1, 1, 1, tzinfo=dt.timezone.utc)

    if end <= created_dt:
        y += 1
        continue
    if start < created_dt:
        start = created_dt
    if start >= now:
        break
    if end > now:
        end = now

    total_all_time += gql(q_total, {
        "login": GH_USER,
        "from": start.isoformat(),
        "to": end.isoformat(),
    })["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    if end >= now:
        break
    y += 1

# streaks based on last 365d (fast)
q_calendar = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""
from_365 = now - dt.timedelta(days=365)
cal = gql(q_calendar, {"login": GH_USER, "from": from_365.isoformat(), "to": now.isoformat()})["user"]["contributionsCollection"]["contributionCalendar"]

days = []
for w in cal["weeks"]:
    for d in w["contributionDays"]:
        days.append((d["date"], int(d["contributionCount"])))
days.sort(key=lambda x: x[0])

def current_streak(days_list):
    m = {dt.date.fromisoformat(d): c for d, c in days_list}
    today = dt.date.today()
    start_day = today if m.get(today, 0) > 0 else (today - dt.timedelta(days=1))
    if m.get(start_day, 0) == 0:
        return 0
    s = 0
    cur = start_day
    while m.get(cur, 0) > 0:
        s += 1
        cur -= dt.timedelta(days=1)
    return s

def longest_streak_365(days_list):
    m = {dt.date.fromisoformat(d): c for d, c in days_list}
    all_dates = sorted(m.keys())
    best = run = 0
    prev = None
    for day in all_dates:
        if prev and (day - prev).days != 1:
            run = 0
        if m[day] > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
        prev = day
    return best

cur = current_streak(days)
longest = longest_streak_365(days)

updated = xml_escape(dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

# Design
title = xml_escape("🚀 GitHub Activity")
sub = xml_escape("All-time contributions with streak signals")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="210" role="img" aria-label="GitHub activity">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>

  <rect width="860" height="210" rx="18" fill="url(#bg)" stroke="#30363d"/>
  <text x="34" y="52" fill="#c9d1d9" font-size="24" font-family="Verdana">{title}</text>
  <text x="34" y="78" fill="#8b949e" font-size="13" font-family="Verdana">{sub}</text>

  <!-- Three mini-cards -->
  <rect x="34"  y="96" width="250" height="78" rx="14" fill="#0b0f14" stroke="#21262d"/>
  <rect x="305" y="96" width="250" height="78" rx="14" fill="#0b0f14" stroke="#21262d"/>
  <rect x="576" y="96" width="250" height="78" rx="14" fill="#0b0f14" stroke="#21262d"/>

  <!-- Total -->
  <text x="54" y="122" fill="#c9d1d9" font-size="15" font-family="Verdana">✨ Total (all-time)</text>
  <text x="54" y="152" fill="#58a6ff" font-size="22" font-family="Verdana">{total_all_time}</text>

  <!-- Current streak -->
  <text x="325" y="122" fill="#c9d1d9" font-size="15" font-family="Verdana">🔥 Current streak</text>
  <text x="325" y="152" fill="#3fb950" font-size="22" font-family="Verdana">{cur} days</text>

  <!-- Longest -->
  <text x="596" y="122" fill="#c9d1d9" font-size="15" font-family="Verdana">🏆 Longest streak</text>
  <text x="596" y="152" fill="#f78166" font-size="22" font-family="Verdana">{longest} days</text>

  <text x="34" y="198" fill="#8b949e" font-size="12" font-family="Verdana">Updated: {updated}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-stats.svg")

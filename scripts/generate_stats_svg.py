import os
import datetime as dt
import requests

GH_TOKEN = os.environ.get("GH_TOKEN")
GH_USER = os.environ.get("GH_USER", "jaafar-harabi")

if not GH_TOKEN:
    raise SystemExit("Missing GH_TOKEN env var")

# Last 365 days
to_date = dt.datetime.utcnow()
from_date = to_date - dt.timedelta(days=365)

query = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

variables = {
    "login": GH_USER,
    "from": from_date.isoformat() + "Z",
    "to": to_date.isoformat() + "Z",
}

resp = requests.post(
    "https://api.github.com/graphql",
    json={"query": query, "variables": variables},
    headers={"Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json"},
    timeout=30,
)
resp.raise_for_status()
data = resp.json()

if "errors" in data:
    raise SystemExit(f"GraphQL errors: {data['errors']}")

cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
total = cal["totalContributions"]

days = []
for w in cal["weeks"]:
    for d in w["contributionDays"]:
        days.append((d["date"], int(d["contributionCount"])))

days.sort(key=lambda x: x[0])  # ascending by date

# Compute current streak (ending today or yesterday depending on activity)
def compute_streak(days_list):
    # map date -> count
    m = {dt.date.fromisoformat(d): c for d, c in days_list}
    today = dt.date.today()

    # GitHub contribution days are in UTC-ish; allow "yesterday" to start streak if today has 0.
    start_day = today if m.get(today, 0) > 0 else (today - dt.timedelta(days=1))

    if m.get(start_day, 0) == 0:
        return 0

    streak = 0
    cur = start_day
    while m.get(cur, 0) > 0:
        streak += 1
        cur -= dt.timedelta(days=1)
    return streak

# Compute longest streak in the period
def longest_streak(days_list):
    m = {dt.date.fromisoformat(d): c for d, c in days_list}
    all_dates = sorted(m.keys())
    best = 0
    run = 0
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

current = compute_streak(days)
longest = longest_streak(days)

# Simple SVG (self-contained, no external fonts)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="160" role="img" aria-label="GitHub stats">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="860" height="160" rx="16" fill="url(#g)" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">GitHub Activity</text>

  <text x="30" y="88" fill="#c9d1d9" font-size="16" font-family="Verdana">Total contributions (365d):</text>
  <text x="320" y="88" fill="#58a6ff" font-size="18" font-family="Verdana">{total}</text>

  <text x="30" y="120" fill="#c9d1d9" font-size="16" font-family="Verdana">Current streak:</text>
  <text x="170" y="120" fill="#3fb950" font-size="18" font-family="Verdana">{current} days</text>

  <text x="360" y="120" fill="#c9d1d9" font-size="16" font-family="Verdana">Longest streak (365d):</text>
  <text x="595" y="120" fill="#f78166" font-size="18" font-family="Verdana">{longest} days</text>

  <text x="30" y="148" fill="#8b949e" font-size="12" font-family="Verdana">Updated: {dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-stats.svg")

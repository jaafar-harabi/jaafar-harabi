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

# -------- GraphQL helper --------
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

# 1) get account createdAt
q_user = """
query($login:String!) {
  user(login:$login) { createdAt }
}
"""
created_at = gql(q_user, {"login": GH_USER})["user"]["createdAt"]
created_dt = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))

# 2) all-time contributions computed year-by-year (safe + accurate)
q_contrib = """
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
year = created_dt.year
while True:
    start = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
    if end <= created_dt:
        year += 1
        continue
    if start < created_dt:
        start = created_dt
    if start >= now:
        break
    if end > now:
        end = now

    total_all_time += gql(q_contrib, {
        "login": GH_USER,
        "from": start.isoformat(),
        "to": end.isoformat(),
    })["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    if end >= now:
        break
    year += 1

# 3) last 365 days for streak computations
to_date = now
from_date = now - dt.timedelta(days=365)

q_calendar = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
cal = gql(q_calendar, {
    "login": GH_USER,
    "from": from_date.isoformat(),
    "to": to_date.isoformat(),
})["user"]["contributionsCollection"]["contributionCalendar"]

days = []
for w in cal["weeks"]:
    for d in w["contributionDays"]:
        days.append((d["date"], int(d["contributionCount"])))
days.sort(key=lambda x: x[0])

def compute_current_streak(days_list):
    m = {dt.date.fromisoformat(d): c for d, c in days_list}
    today = dt.date.today()
    start_day = today if m.get(today, 0) > 0 else (today - dt.timedelta(days=1))
    if m.get(start_day, 0) == 0:
        return 0
    streak = 0
    cur = start_day
    while m.get(cur, 0) > 0:
        streak += 1
        cur -= dt.timedelta(days=1)
    return streak

def longest_streak_365(days_list):
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

current = compute_current_streak(days)
longest = longest_streak_365(days)

title = xml_escape("GitHub Activity (All-time)")
updated = xml_escape(dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="170" role="img" aria-label="GitHub activity all-time">
  <rect width="860" height="170" rx="16" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="48" fill="#c9d1d9" font-size="22" font-family="Verdana">{title}</text>

  <text x="30" y="88" fill="#c9d1d9" font-size="16" font-family="Verdana">Total contributions (all-time):</text>
  <text x="330" y="88" fill="#58a6ff" font-size="18" font-family="Verdana">{total_all_time}</text>

  <text x="30" y="122" fill="#c9d1d9" font-size="16" font-family="Verdana">Current streak:</text>
  <text x="170" y="122" fill="#3fb950" font-size="18" font-family="Verdana">{current} days</text>

  <text x="360" y="122" fill="#c9d1d9" font-size="16" font-family="Verdana">Longest streak (365d):</text>
  <text x="600" y="122" fill="#f78166" font-size="18" font-family="Verdana">{longest} days</text>

  <text x="30" y="150" fill="#8b949e" font-size="12" font-family="Verdana">Updated: {updated}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wrote assets/github-stats.svg")

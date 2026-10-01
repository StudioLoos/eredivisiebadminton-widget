#!/usr/bin/env python3
"""Bepaalt of de update nu moet draaien: van 60 min voor tot 5 uur na de aanvang van een wedstrijd.
Exit 0 = draaien, exit 1 = overslaan."""
import json, os, sys, datetime
from zoneinfo import ZoneInfo
if os.environ.get("FORCE") == "1":
    sys.exit(0)
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.json")
try:
    sched = json.load(open(p))
except Exception:
    sys.exit(0)  # geen schema: gewoon ophalen
now = datetime.datetime.now(ZoneInfo("Europe/Amsterdam")).replace(tzinfo=None)
for s in sched:
    t = datetime.datetime.fromisoformat(s["start"] if isinstance(s, dict) else s)
    if t - datetime.timedelta(minutes=60) <= now <= t + datetime.timedelta(hours=5):
        print("Wedstrijdvenster:", t.isoformat())
        sys.exit(0)
print("Geen wedstrijd rond dit moment, overslaan.")
sys.exit(1)

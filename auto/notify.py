#!/usr/bin/env python3
"""Verstuurt klaargezette meldingen (pending_events.json) via OneSignal naar de app.
Instellingen in onesignal.json naast dit script: {"app_id": "...", "rest_key": "..."}.
Zonder onesignal.json worden de meldingen alleen gelogd en opgeruimd. Faalt nooit hard."""
import json, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
PE = os.path.join(HERE, "pending_events.json"); CFG = os.path.join(HERE, "onesignal.json")
APP_URL = "https://app.eredivisiebadminton.nl/app.html"
def main():
    try: ev = json.load(open(PE, encoding="utf-8"))
    except Exception: return
    os.remove(PE)
    if not os.path.exists(CFG):
        for e in ev: print("MELDING (niet verstuurd, geen OneSignal ingesteld):", e["title"])
        return
    c = json.load(open(CFG))
    for e in ev:
        body = {"app_id": c["app_id"], "target_channel": "push",
                "filters": [{"field": "tag", "key": e["type"], "relation": "=", "value": "1"}],
                "headings": {"en": e["title"], "nl": e["title"]}, "contents": {"en": e["body"], "nl": e["body"]},
                "url": APP_URL, "web_push_topic": e["type"]}
        req = urllib.request.Request("https://api.onesignal.com/notifications", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Key " + c["rest_key"]})
        try:
            with urllib.request.urlopen(req, timeout=20) as r: print("MELDING verstuurd:", e["title"], r.status)
        except Exception as x: print("MELDING mislukt:", e["title"], x)
if __name__ == "__main__":
    try: main()
    except Exception as x: print("notify fout:", x)
    sys.exit(0)

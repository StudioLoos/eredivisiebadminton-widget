#!/usr/bin/env python3
"""Haalt de ruwe Eredivisie-gegevens op van badmintonnederland.toernooi.nl (zelfde uitvoer als collect.js).
Werkt zonder browser: accepteert alleen de noodzakelijke cookies van toernooi.nl.
Gebruik: collect.py raw.json"""
import json, re, sys, time
import requests
from bs4 import BeautifulSoup

BASE = "https://badmintonnederland.toernooi.nl"
P = "9A42A3C8-BE3A-4EB6-AEEB-8D7D562D964E"
UA = "Mozilla/5.0 (compatible; EredivisieBadmintonWidget/1.0; +https://www.eredivisiebadminton.nl)"
CODE = re.compile(r"^(MD|VD|ME\d|VE\d|GD\d)$")

s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "nl-NL,nl;q=0.9"})


def consent():
    # Alleen noodzakelijke cookies (CookiePurposes=1)
    s.get(BASE + "/cookiewall/?returnurl=%2F", timeout=30)
    s.post(BASE + "/cookiewall/Save", data={"ReturnUrl": "/", "SettingsOpen": "false", "CookiePurposes": "1"},
           timeout=30, allow_redirects=False)


def get(path):
    url = BASE + path + ("&" if "?" in path else "?") + "_=%d" % int(time.time() * 1000)
    for attempt in range(3):
        r = s.get(url, timeout=30, allow_redirects=False)
        if r.status_code in (301, 302) and "cookiewall" in r.headers.get("location", ""):
            consent()
            continue
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    raise RuntimeError("cookiemelding blijft terugkomen")


def cell(td, sep=" "):
    t = td.get_text(sep)
    if sep == "\n":
        return "\n".join(x.strip() for x in t.split("\n") if x.strip())
    return re.sub(r"\s+", " ", t).strip()


def cells(tr, sep=" "):
    return [cell(td, sep) for td in tr.find_all(["td", "th"], recursive=False)]


def main(out):
    consent()
    dr = get("/sport/league/draw?id=%s&draw=1" % P)
    rows = dr.find_all("tr")
    stand = [c for c in (cells(tr) for tr in rows) if c and re.match(r"^\d+$", c[0]) and len(c) >= 10]
    seen, lst = set(), []
    for tr in rows:
        a = tr.find("a", href=re.compile("teammatch"))
        if not a:
            continue
        m = re.search(r"match=(\d+)", a["href"])
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        lst.append({"id": m.group(1), "c": cells(tr)})
    matches = {}
    for m in lst:
        d = get("/sport/teammatch.aspx?id=%s&match=%s" % (P, m["id"]))
        matches[m["id"]] = [c for c in (cells(tr, "\n") for tr in d.find_all("tr")) if c and CODE.match(c[0])]
    ps = get("/sport/playerstats.aspx?id=%s&draw=1" % P)
    players = []
    for tr in ps.find_all("tr"):
        a = tr.find("a", href=re.compile("player="))
        if a:
            players.append({"pid": int(a["href"].split("player=")[1].split("&")[0]), "c": cells(tr)})
    if not stand or not players:
        raise SystemExit("FOUT bij ophalen: geen gegevens (cookiemelding of site niet bereikbaar)")
    json.dump({"stand": stand, "list": lst, "matches": matches, "players": players},
              open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("opgehaald: %d wedstrijden, %d spelers" % (len(lst), len(players)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw.json")

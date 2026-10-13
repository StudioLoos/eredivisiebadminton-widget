#!/usr/bin/env python3
"""Haalt de ruwe Eredivisie-gegevens op van badmintonnederland.toernooi.nl (zelfde uitvoer als collect.js).
Werkt zonder browser: accepteert alleen de noodzakelijke cookies van toernooi.nl.
Gebruik: collect.py raw.json"""
import json, os, re, sys, time, unicodedata
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


# ── Nationale ranking (Badminton Nederland) ────────────────────────────────────
RANK_CATS = {"Mannen Enkel": ("HE", "Herenenkel"), "Vrouwen Enkel": ("DE", "Damesenkel"),
             "Mannen Dubbel": ("HD", "Herendubbel"), "Vrouwen Dubbel": ("DD", "Damesdubbel"),
             "Gemengd Dubbel": ("GD", "Gemengd dubbel")}
RANK_PAGES = 8   # max. 8 x 100 plaatsen per onderdeel


def norm(n):
    n = unicodedata.normalize("NFD", n)
    return re.sub(r"\s+", " ", "".join(c for c in n if unicodedata.category(c) != "Mn")).strip().lower()


def ranking(names, old):
    """Nationale ranking voor de Eredivisiespelers. Hergebruikt de vorige uitkomst als de publicatie
    en de spelerslijst niet veranderd zijn (scheelt tientallen verzoeken per run)."""
    ov = get("/ranking/ranking.aspx?rid=75")
    a = ov.find("a", href=re.compile(r"ranking\.aspx\?id=\d+"))
    if not a:
        raise RuntimeError("geen rankingpublicatie gevonden")
    rid = int(re.search(r"id=(\d+)", a["href"]).group(1))
    want = sorted(set(names))
    if old and old.get("id") == rid and old.get("checked") == want:
        return old
    pg = get("/ranking/ranking.aspx?id=%d" % rid)
    opt = pg.find("option", attrs={"value": str(rid)})
    week = opt.get_text(strip=True) if opt else ""
    cats = []
    for link in pg.find_all("a", href=re.compile(r"category\.aspx\?id=%d&category=\d+" % rid)):
        label = link.get_text(strip=True)
        if label not in RANK_CATS or any(c["cat"] == int(re.search(r"category=(\d+)", link["href"]).group(1)) for c in cats):
            continue
        cats.append({"cat": int(re.search(r"category=(\d+)", link["href"]).group(1)), "naam": label})
    byn = {norm(n): n for n in want}
    out = []
    for c in cats:
        code, label = RANK_CATS[c["naam"]]
        rows, todo = [], set(byn)
        for p in range(1, RANK_PAGES + 1):
            d = get("/ranking/category.aspx?id=%d&category=%d&p=%d&ps=100" % (rid, c["cat"], p))
            n_rows = 0
            for tr in d.find_all("tr"):
                pa = tr.find("a", href=re.compile(r"player\.aspx\?id=\d+&player=\d+"))
                v = cells(tr)
                if not pa or not v or not v[0].isdigit():
                    continue
                n_rows += 1
                k = norm(pa.get_text(" ", strip=True))
                if k in todo:
                    todo.discard(k)
                    num = [x for x in v if re.fullmatch(r"\d+", x)]
                    rows.append({"r": int(v[0]), "n": byn[k], "pt": int(num[-2]) if len(num) >= 3 else None,
                                 "w": int(num[-1]) if len(num) >= 3 else None,
                                 "pid": int(re.search(r"player=(\d+)", pa["href"]).group(1))})
            if not todo or n_rows < 100:
                break
        out.append({"code": code, "label": label, "rows": rows})
    order = [v[0] for v in RANK_CATS.values()]
    out.sort(key=lambda c: order.index(c["code"]))
    if not any(c["rows"] for c in out):
        raise RuntimeError("ranking leeg")
    return {"id": rid, "week": week, "cats": out, "checked": want}


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
    # volledig speelschema (alleen de lijst, zonder wedstrijdpagina's): voor het tabblad Programma
    alle = []
    try:
        dm = get("/sport/drawmatches.aspx?id=%s&draw=1" % P)
        for tr in dm.find_all("tr"):
            a = tr.find("a", href=re.compile("teammatch"))
            m = re.search(r"match=(\d+)", a["href"]) if a else None
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                alle.append({"id": m.group(1), "c": cells(tr)})
    except Exception as e:
        print("speelschema niet opgehaald:", e)
    ps = get("/sport/playerstats.aspx?id=%s&draw=1" % P)
    players = []
    for tr in ps.find_all("tr"):
        a = tr.find("a", href=re.compile("player="))
        if a:
            players.append({"pid": int(a["href"].split("player=")[1].split("&")[0]), "c": cells(tr)})
    if not stand or not players:
        raise SystemExit("FOUT bij ophalen: geen gegevens (cookiemelding of site niet bereikbaar)")
    # nationale ranking (fouten hier mogen de rest niet tegenhouden)
    rk = None
    try:
        try: prev = json.load(open("data.json", encoding="utf-8")).get("ranking")
        except Exception: prev = None
        rk = ranking([p["c"][1] for p in players if len(p["c"]) > 1], prev)
        print("ranking %s: %s" % (rk["week"], ", ".join("%s %d" % (c["code"], len(c["rows"])) for c in rk["cats"])))
    except Exception as e:
        print("ranking niet opgehaald:", e)
    json.dump({"stand": stand, "list": lst, "matches": matches, "players": players, "alle": alle, "ranking": rk},
              open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("opgehaald: %d wedstrijden (+%d in speelschema), %d spelers" % (len(lst), len(alle), len(players)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw.json")

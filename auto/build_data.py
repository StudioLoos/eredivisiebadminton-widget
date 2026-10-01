#!/usr/bin/env python3
"""Bouwt data.json voor de widget uit de ruwe gegevens van collect.js (Python 3.9+).
Gebruik: build_data.py raw.json bestaande_data.json uit_data.json"""
import json, re, sys, datetime

TEAMS = {"DUINWIJCK BC 1": "BC Duinwijck", "DUNLOP DKC 1": "Dunlop DKC", "ROOSTERSE BC 1": "PK Keukens Roosterse",
         "DROP SHOT BC 1": "BC Drop Shot", "ALMERE BV 1": "FIT Almere", "VELO BADMINTON 1": "Velo Badminton",
         "2dA SMASHING BC 1": "2dA Smashing", "Decorette AMERSFOORT 1": "Decorette Amersfoort", "AMERSFOORT 1": "Decorette Amersfoort"}
MAAND = ["", "januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"]
MKORT = ["", "jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
DAG = {"ma": "ma", "di": "di", "wo": "wo", "do": "do", "vr": "vr", "za": "za", "zo": "zo"}

def team(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*\(\d+-\d+\)$", "", s)
    return TEAMS.get(s, TEAMS.get(s.upper(), s.title()))

def names(s):
    return [x.strip() for x in re.split(r"[\n/]", s) if x.strip()]

def rubber(c):
    code, hp, ap, sc = c[0], c[1], c[3] if len(c) > 3 else "", c[4] if len(c) > 4 else ""
    sc = re.sub(r"\s+", " ", sc).strip()
    r = {"code": code, "home": names(hp), "away": names(ap)}
    if sc:
        mo = re.search(r"Opgave Team (\d)", sc, re.I)
        g = re.findall(r"(\d+)-(\d+)", sc)
        if mo:
            r["winner"] = "away" if mo.group(1) == "1" else "home"
            r["score"] = (" ".join("%s-%s" % x for x in g) + " (opgave)").strip()
        elif g:
            h = sum(int(a) > int(b) for a, b in g); a_ = sum(int(b) > int(a) for a, b in g)
            r["score"] = " ".join("%s-%s" % x for x in g)
            if h >= 2: r["winner"] = "home"
            elif a_ >= 2: r["winner"] = "away"
    return r

def parse_list(item):
    c = [x for x in item["c"]]
    tm = next((x for x in c if re.match(r"^(ma|di|wo|do|vr|za|zo) \d+-\d+-\d{4} \d+:\d+", x)), "")
    i = c.index(tm) if tm in c else 0
    rnd = int(c[i + 1]) if i + 1 < len(c) and c[i + 1].isdigit() else 0
    dash = c.index("-", i) if "-" in c[i:] else None
    home = team(c[dash - 1]) if dash else ""
    away = team(c[dash + 1]) if dash else ""
    m = re.match(r"^(\w+) (\d+)-(\d+)-(\d{4}) (\d+:\d+)", tm)
    d = datetime.date(int(m.group(4)), int(m.group(3)), int(m.group(2))) if m else None
    when = "%s %d %s · %s" % (m.group(1), d.day, MKORT[d.month], m.group(5)) if m else ""
    start = None
    if m:
        hh, mm = m.group(5).split(":")
        start = datetime.datetime(d.year, d.month, d.day, int(hh), int(mm)).isoformat()
    return {"id": item["id"], "round": rnd, "home": home, "away": away, "date": d, "when": when, "start": start}

def round_date(ds):
    ds = sorted(set(x for x in ds if x))
    if not ds: return ""
    if len(ds) == 1: return "%d %s %d" % (ds[0].day, MAAND[ds[0].month], ds[0].year)
    if ds[0].month == ds[-1].month: return "%s & %d %s %d" % (" & ".join(str(x.day) for x in ds[:-1]), ds[-1].day, MAAND[ds[-1].month], ds[-1].year)
    return " & ".join("%d %s" % (x.day, MAAND[x.month]) for x in ds) + " %d" % ds[-1].year

CATS = [("HE", "Herenenkel", ("ME1", "ME2")), ("DE", "Damesenkel", ("VE1", "VE2")), ("HD", "Herendubbel", ("MD",)),
        ("DD", "Damesdubbel", ("VD",)), ("GD", "Gemengd dubbel", ("GD1", "GD2"))]

def mvp(seizoen, clubs):
    """MVP per speelronde: gewonnen, gamesaldo, puntensaldo, puntenpercentage, sterkte tegenstander."""
    sw, sp = {}, {}
    for R in seizoen:
        for m in R["matches"]:
            for r in m["rows"]:
                if not r.get("winner"): continue
                for side in ("home", "away"):
                    for n in r[side]:
                        sp[n] = sp.get(n, 0) + 1; sw[n] = sw.get(n, 0) + (r["winner"] == side)
    strength = lambda ns: sum(sw.get(n, 0) / max(1, sp.get(n, 0)) for n in ns) / max(1, len(ns))
    out = []
    for R in seizoen:
        ents = {}
        def add(key, club, cat, w, gw, gl, pw, pl, opp, res):
            e = ents.setdefault(key, {"names": list(key[1]), "club": club, "cat": cat, "w": 0, "p": 0, "gw": 0, "gl": 0, "pw": 0, "pl": 0, "opp": [], "res": []})
            e["w"] += w; e["p"] += 1; e["gw"] += gw; e["gl"] += gl; e["pw"] += pw; e["pl"] += pl; e["opp"].append(opp); e["res"].append(res)
        complete = all(m.get("hs", "") != "" and (m["hs"] + m["as"]) >= 8 for m in R["matches"]) and len(R["matches"]) >= 4
        for m in R["matches"]:
            for r in m["rows"]:
                if not r.get("winner"): continue
                cat = next(c for c, _, codes in CATS if r["code"] in codes)
                opg = "opgave" in (r.get("score") or "")
                g = [] if opg else [(int(a), int(b)) for a, b in re.findall(r"(\d+)-(\d+)", r.get("score") or "")]
                for side, oth in (("home", "away"), ("away", "home")):
                    w = int(r["winner"] == side)
                    sc = [(a, b) if side == "home" else (b, a) for a, b in g]
                    gw = sum(a > b for a, b in sc); gl = sum(b > a for a, b in sc)
                    pw = sum(a for a, b in sc); pl = sum(b for a, b in sc)
                    res = {"code": r["code"], "tegen": r[oth], "tclub": m[oth], "w": w,
                           "score": " ".join("%d-%d" % x for x in sc) + (" (opgave)" if opg else "")}
                    st = strength(r[oth])
                    add((cat, tuple(r[side])), m[side], cat, w, gw, gl, pw, pl, st, res)
                    for n in r[side]:
                        add(("ALL", (n,)), m[side], "ALL", w, gw, gl, pw, pl, st, res)
        def rank(e):
            return (e["w"], e["gw"] - e["gl"], e["pw"] - e["pl"], e["pw"] / max(1, e["pw"] + e["pl"]), sum(e["opp"]) / len(e["opp"]))
        def pub(e):
            return {"names": e["names"], "club": e["club"], "w": e["w"], "p": e["p"], "games": "%d-%d" % (e["gw"], e["gl"]),
                    "punten": "%d-%d" % (e["pw"], e["pl"]), "saldo": e["pw"] - e["pl"], "res": e["res"]}
        def top(cat, k):
            L = sorted((e for e in ents.values() if e["cat"] == cat), key=lambda e: (rank(e), [-ord(ch) for ch in " ".join(e["names"])]), reverse=True)
            return [pub(e) for e in L[:k]]
        if not ents: continue
        out.append({"round": R["round"], "date": R.get("date", ""), "voorlopig": not complete,
                    "speler": top("ALL", 3),
                    "cats": [dict(code=c, label=l, top=top(c, 3)) for c, l, _ in CATS]})
    return out

def events(old, new):
    """Nieuwe gebeurtenissen voor pushmeldingen: afgeronde uitslag, bekende opstelling, MVP's compleet."""
    out = []
    def done(m): return m.get("hs", "") != "" and (m["hs"] + m["as"]) >= 8
    prev = {(R["round"], m["home"], m["away"]): m for R in old.get("seizoen", []) for m in R["matches"]}
    for R in new.get("seizoen", []):
        for m in R["matches"]:
            p = prev.get((R["round"], m["home"], m["away"]))
            if done(m) and not (p and done(p)) and old.get("seizoen"):
                out.append({"type": "uitslag", "title": "Uitslag: %s – %s" % (m["home"], m["away"]),
                            "body": "%s %s – %s %s · %s" % (m["home"], m["hs"], m["as"], m["away"], R["round"]),
                            "clubs": [m["home"], m["away"]]})
    po = {(m["home"], m["away"]): m for m in (old.get("programma") or {}).get("matches", [])}
    for m in (new.get("programma") or {}).get("matches", []):
        has = any(r.get("home") for r in m.get("rows", []))
        p = po.get((m["home"], m["away"])); had = p and any(r.get("home") for r in p.get("rows", []))
        if has and not had and old.get("programma"):
            out.append({"type": "opstelling", "title": "Opstelling bekend: %s – %s" % (m["home"], m["away"]),
                        "body": "Bekijk wie er vandaag op de baan staat · %s" % m.get("when", ""),
                        "clubs": [m["home"], m["away"]]})
    om = {R["round"]: R for R in old.get("mvp", [])}
    for R in new.get("mvp", []):
        if not R.get("voorlopig") and (om.get(R["round"], {"voorlopig": True}).get("voorlopig", True)) and old.get("mvp") is not None:
            names = ", ".join(" & ".join(c["top"][0]["names"]) for c in R["cats"] if c["top"])
            out.append({"type": "mvp", "title": "De MVP's van %s zijn bekend" % R["round"].lower(), "body": names})
    return out

def main(raw_p, old_p, out_p):
    raw = json.load(open(raw_p, encoding="utf-8"))
    try: old = json.load(open(old_p, encoding="utf-8"))
    except Exception: old = {}
    lst = [parse_list(x) for x in raw["list"]]
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    sched_p = os.path.join(here, "schedule.json")
    rm = {}
    for m in lst:
        rows = [rubber(c) for c in raw["matches"].get(m["id"], [])]
        m["rows"] = rows
        m["played"] = any(r.get("winner") for r in rows)
        m["hs"] = sum(r.get("winner") == "home" for r in rows) if m["played"] else ""
        m["as"] = sum(r.get("winner") == "away" for r in rows) if m["played"] else ""
        rm.setdefault(m["round"], []).append(m)
    # speelschema + moment waarop een wedstrijd klaar was (voor het ophaalvenster in update_widget.sh)
    dt_p = os.path.join(here, "done_times.json")
    try: done_times = json.load(open(dt_p))
    except Exception: done_times = {}
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")
    sched = []
    for m in lst:
        if not m.get("start"): continue
        key = "%s|%s|%s" % (m["start"], m["home"], m["away"])
        done = m["played"] and (m["hs"] + m["as"]) >= 8
        if done and key not in done_times:
            st = datetime.datetime.fromisoformat(m["start"])
            # al lang voorbij bij eerste waarneming: schat het einde op 4 uur na aanvang
            done_times[key] = (st + datetime.timedelta(hours=4)).isoformat(timespec="seconds") if datetime.datetime.now() - st > datetime.timedelta(hours=7) else now_iso
        lineup = any(r.get("home") and r.get("away") for r in m["rows"])
        sched.append({"start": m["start"], "home": m["home"], "away": m["away"], "lineup": lineup, "done_at": done_times.get(key)})
    json.dump(sorted(sched, key=lambda x: x["start"]), open(sched_p, "w"), ensure_ascii=False, indent=0)
    json.dump(done_times, open(dt_p, "w"), ensure_ascii=False)
    played = sorted(r for r, ms in rm.items() if any(m["played"] for m in ms))
    if not played: raise SystemExit("geen gespeelde speelronde gevonden")
    N = played[-1]
    later = sorted(r for r in rm if r > N)
    nxt = later[0] if later else None
    cur = sorted(rm[N], key=lambda m: (m["date"] or datetime.date.min, m["when"]))
    matches = [{"home": m["home"], "away": m["away"], "hs": m["hs"], "as": m["as"], "rows": m["rows"]} for m in cur]
    data = {"round": "Speelronde %d" % N, "date": round_date([m["date"] for m in cur]), "matches": matches}
    # seizoen: bestaande rondes behouden, rondes uit de lijst vervangen/toevoegen
    seizoen = {R["round"]: R for R in old.get("seizoen", [])}
    for r in played:
        ms = sorted(rm[r], key=lambda m: (m["date"] or datetime.date.min, m["when"]))
        key = "Speelronde %d" % r
        prev = seizoen.get(key, {"matches": []})
        merged = {(m["home"], m["away"]): m for m in prev.get("matches", [])}
        for m in ms:
            merged[(m["home"], m["away"])] = {"home": m["home"], "away": m["away"], "hs": m["hs"], "as": m["as"], "rows": m["rows"]}
        order = [(m["home"], m["away"]) for m in prev.get("matches", [])]
        order += [k for k in ((m["home"], m["away"]) for m in ms) if k not in order]
        seizoen[key] = {"round": key, "date": prev.get("date") or re.sub(r" \d{4}$", "", round_date([m["date"] for m in ms])),
                        "matches": [merged[k] for k in order]}
    data["seizoen"] = sorted(seizoen.values(), key=lambda R: -int(R["round"].split()[-1]))
    # programma
    if nxt:
        ms = sorted(rm[nxt], key=lambda m: (m["date"] or datetime.date.min, m["when"]))
        data["programma"] = {"round": "Speelronde %d" % nxt, "date": round_date([m["date"] for m in ms]),
                             "matches": [{"home": m["home"], "away": m["away"], "when": m["when"],
                                          "rows": [{"code": r["code"], "home": r["home"], "away": r["away"]} for r in m["rows"] if r["home"] and r["away"]]} for m in ms]}
    # stand
    st = []
    for c in raw["stand"]:
        v = [x for x in c]
        st.append({"pos": int(v[0]), "team": team(v[1]), "pts": int(v[2]), "gp": int(v[3]), "w": int(v[4]), "g": int(v[5]), "v": int(v[6]),
                   "wed": "%s – %s" % (v[7], v[9]), "games": "%s – %s" % (v[10], v[12])})
    data["stand"] = st
    # spelers
    sp, ids = [], {}
    for p in raw["players"]:
        c = p["c"]
        sp.append({"pos": int(c[0]), "speler": c[1], "club": team(c[2]), "w": int(c[3]), "gp": int(c[4]),
                   "games": re.sub(r"\s*-\s*", " – ", c[5]), "punten": re.sub(r"\s*-\s*", " – ", c[6])})
        ids[c[1]] = p["pid"]
    data["spelers"] = sp; data["top10"] = sp[:10]; data["ids"] = ids
    import os
    pp = os.path.join(os.path.dirname(os.path.abspath(out_p)), "photos.json")
    for cand in (os.path.join(os.path.dirname(os.path.abspath(old_p)), "fotos", "photos.json"),):
        if os.path.exists(cand):
            data["photos"] = json.load(open(cand, encoding="utf-8"))
    # per team: enkel/dubbel/mix uit alle wedstrijden van het seizoen
    agg = {}
    for R in data["seizoen"]:
        for m in R["matches"]:
            for r in m["rows"]:
                if not r.get("winner"): continue
                cat = "e" if r["code"][:2] in ("ME", "VE") else "d" if r["code"] in ("MD", "VD") else "m"
                for side in ("home", "away"):
                    for n in r[side]:
                        a = agg.setdefault(n, {"club": m[side], "e": [0, 0], "d": [0, 0], "m": [0, 0], "w": 0, "g": 0})
                        won = r["winner"] == side
                        a[cat][0 if won else 1] += 1; a["g"] += 1; a["w"] += won
    gd = {s["speler"]: (lambda g: int(g[0]) - int(g[1]))(re.findall(r"\d+", s["games"]) or [0, 0]) for s in sp}
    teams = []
    for s in st:
        rows = [(n, a) for n, a in agg.items() if a["club"] == s["team"]]
        rows.sort(key=lambda x: (-x[1]["w"], x[1]["g"], -gd.get(x[0], 0)))
        f = lambda v: "%d – %d" % tuple(v) if sum(v) else "–"
        teams.append({"team": s["team"], "rows": [{"pos": i + 1, "speler": n, "e": f(a["e"]), "d": f(a["d"]), "m": f(a["m"]), "tot": "%d/%d" % (a["w"], a["g"])} for i, (n, a) in enumerate(rows)]})
    data["teams"] = teams
    data["mvp"] = mvp(data["seizoen"], [x["team"] for x in st])
    # controle: totalen per speler moeten gelijk zijn aan toernooi.nl
    diff = [s["speler"] for s in sp if s["speler"] in agg and (agg[s["speler"]]["w"], agg[s["speler"]]["g"]) != (s["w"], s["gp"])]
    data["check"] = {"afwijkingen": diff}
    cmp_old = {k: v for k, v in old.items() if k not in ("updated", "check")}
    cmp_new = {k: v for k, v in data.items() if k not in ("updated", "check")}
    changed = json.dumps(cmp_old, sort_keys=True, ensure_ascii=False) != json.dumps(cmp_new, sort_keys=True, ensure_ascii=False)
    data["updated"] = datetime.datetime.now().strftime("%d-%m-%Y %H:%M") if changed else old.get("updated", "")
    json.dump(data, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if changed:
        ev = events(old, data)
        if ev:
            pe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_events.json")
            try: cur = json.load(open(pe, encoding="utf-8"))
            except Exception: cur = []
            json.dump(cur + ev, open(pe, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("MELDINGEN klaargezet:", len(ev))
    print("CHANGED" if changed else "UNCHANGED", "ronde", N, "afwijkingen:", diff)

if __name__ == "__main__":
    main(*sys.argv[1:4])

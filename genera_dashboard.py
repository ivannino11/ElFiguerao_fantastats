import json
import os
import glob
import pandas as pd

RUOLI = {1: "P", 2: "D", 3: "C", 4: "A"}
RUOLI_CLASSE = {1: "badge-p", 2: "badge-d", 3: "badge-c", 4: "badge-a"}

def calcola_gol(pt):
    if pt < 66.0:
        return 0
    return int((pt - 66.0) // 6) + 1

def genera_sito():
    # 1. Carica dati
    with open("giocatori_rose.json", "r", encoding="utf-8") as f:
        players = {p["id"]: p for p in json.load(f)["players"]}

    with open("squadre_fanta.json", "r", encoding="utf-8") as f:
        teams_raw = json.load(f)["data"]
        teams_map = {t["id"]: t for t in teams_raw}

    with open("status.json", "r", encoding="utf-8") as f:
        status_data = json.load(f)

    with open("calendario.json", "r", encoding="utf-8") as f:
        calendario = json.load(f)

    # 2. Carica tutte le giornate disponibili
    lineup_files = sorted(glob.glob("lineup_giornata_*.json"), key=lambda x: int(x.split("_")[-1].split(".")[0]))
    
    giornate_data = []
    tutti_rimpianti = []
    moduli_stats = {}
    player_stats = {} # pid -> {'gol': 0, 'assist': 0, 'amm': 0, 'esp': 0, 'voti': [], 'fv': [], 'clean_sheets': 0}
    best_scores = {} # (g_num, tid) -> best_score

    for fpath in lineup_files:
        g_num = int(fpath.split("_")[-1].split(".")[0])
        with open(fpath, "r", encoding="utf-8") as f:
            lineup = json.load(f)

        giornata_obj = {"giornata": g_num, "squadre": []}

        for t in lineup:
            tid = t["tid"]
            tinfo = teams_map.get(tid, {})
            tname = tinfo.get("n", f"Squadra {tid}")
            allenatore = tinfo.get("nu", "")
            tot_punti = t.get("tot", 0)
            punti_gara = t.get("points", 0)
            modulo = t.get("mdl", "N/D")

            # Statistiche modulo
            if modulo not in moduli_stats:
                moduli_stats[modulo] = {"usato": 0, "tot_punti": 0, "vittorie": 0, "pareggi": 0, "sconfitte": 0}
            moduli_stats[modulo]["usato"] += 1
            moduli_stats[modulo]["tot_punti"] += tot_punti
            if punti_gara == 3:
                moduli_stats[modulo]["vittorie"] += 1
            elif punti_gara == 1:
                moduli_stats[modulo]["pareggi"] += 1
            else:
                moduli_stats[modulo]["sconfitte"] += 1

            # Sostituzioni effettuate
            sub_in = set()
            swtc_str = t.get("swtc") or ""
            if swtc_str:
                parts = swtc_str.split(";")
                if len(parts) >= 2:
                    try:
                        sub_in.add(int(parts[1]))
                    except ValueError:
                        pass

            starters = t.get("starts", [])
            bench = t.get("bench", [])

            # Aggrega stats individuali per tutti i giocatori scesi in campo o in panchina
            for p in starters + bench:
                pid = p["pid"]
                if pid not in player_stats:
                    player_stats[pid] = {'gol': 0, 'assist': 0, 'amm': 0, 'esp': 0, 'voti': [], 'fv': [], 'clean_sheet': 0}
                
                scr = p.get("scr")
                cscr = p.get("cscr")
                if scr != 56 and isinstance(cscr, (int, float)) and cscr < 50:
                    player_stats[pid]['voti'].append(scr)
                    player_stats[pid]['fv'].append(cscr)

                b = (p.get("b") or "").split(";")
                if len(b) > 2 and b[2]: player_stats[pid]['gol'] += int(b[2])
                if len(b) > 6 and b[6]: player_stats[pid]['gol'] += int(b[6])
                if len(b) > 12 and b[12]: player_stats[pid]['assist'] += int(b[12])
                if len(b) > 13 and b[13]: player_stats[pid]['assist'] += int(b[13])
                if len(b) > 0 and b[0]: player_stats[pid]['amm'] += int(b[0])
                if len(b) > 5 and b[5]: player_stats[pid]['esp'] += int(b[5])
                if len(b) > 10 and b[10]: player_stats[pid]['clean_sheet'] += int(b[10])

            # Calcolo Best XI per What-If
            delta_max = 0.0
            for role_id, role_code in RUOLI.items():
                st_role = [p for p in starters if players.get(p["pid"], {}).get("fcrle") == role_id and isinstance(p.get("cscr"), (int, float)) and p.get("cscr") < 50]
                bn_role = [p for p in bench if p["pid"] not in sub_in and players.get(p["pid"], {}).get("fcrle") == role_id and isinstance(p.get("cscr"), (int, float)) and p.get("cscr") < 50 and p.get("scr") != 56]
                
                st_sorted = sorted(st_role, key=lambda x: x["cscr"])
                bn_sorted = sorted(bn_role, key=lambda x: x["cscr"], reverse=True)
                
                for s_bad, b_good in zip(st_sorted, bn_sorted):
                    if b_good["cscr"] > s_bad["cscr"]:
                        delta_max += (b_good["cscr"] - s_bad["cscr"])
            
            best_scores[(g_num, tid)] = round(tot_punti + delta_max, 1)

            # Panchina e Rimpianti
            rimpianti_squadra = []
            for p in bench:
                pid = p.get("pid")
                if pid in sub_in:
                    continue  # È subentrato

                scr = p.get("scr")
                cscr = p.get("cscr")
                if scr == 56 or cscr is None or cscr >= 50:
                    continue

                b = (p.get("b") or "").split(";")
                gol = int(b[2]) if len(b) > 2 and b[2] else 0
                rig_gol = int(b[6]) if len(b) > 6 and b[6] else 0
                tot_gol = gol + rig_gol
                assist = (int(b[12]) if len(b) > 12 and b[12] else 0) + (int(b[13]) if len(b) > 13 and b[13] else 0)
                clean_sheet = int(b[10]) if len(b) > 10 and b[10] else 0

                if tot_gol > 0 or assist > 0 or cscr >= 7.0:
                    pinfo = players.get(pid, {})
                    r_item = {
                        "pid": pid,
                        "nome": pinfo.get("name", f"ID {pid}"),
                        "squadra_serie_a": pinfo.get("stnme", ""),
                        "ruolo": RUOLI.get(pinfo.get("fcrle"), "?"),
                        "ruolo_classe": RUOLI_CLASSE.get(pinfo.get("fcrle"), "badge-c"),
                        "voto": scr,
                        "fantavoto": cscr,
                        "gol": tot_gol,
                        "assist": assist,
                        "clean_sheet": clean_sheet,
                        "squadra": tname,
                        "giornata": g_num
                    }
                    rimpianti_squadra.append(r_item)
                    tutti_rimpianti.append(r_item)

            giornata_obj["squadre"].append({
                "tid": tid,
                "nome": tname,
                "allenatore": allenatore,
                "tot": tot_punti,
                "best_tot": best_scores[(g_num, tid)],
                "modulo": modulo,
                "punti_gara": punti_gara,
                "rimpianti": rimpianti_squadra
            })

        giornate_data.append(giornata_obj)

    # 3. Classifica Rimpianti
    df_rimpianti = pd.DataFrame(tutti_rimpianti)
    classifica_rimpianti = []
    for tid, tinfo in teams_map.items():
        tname = tinfo["n"]
        df_team = df_rimpianti[df_rimpianti["squadra"] == tname] if not df_rimpianti.empty else pd.DataFrame()
        gol_panc = int(df_team["gol"].sum()) if not df_team.empty else 0
        assist_panc = int(df_team["assist"].sum()) if not df_team.empty else 0
        tot_rimpianti = len(df_team) if not df_team.empty else 0
        avg_fv = round(df_team["fantavoto"].mean(), 2) if not df_team.empty else 0.0
        classifica_rimpianti.append({
            "squadra": tname,
            "allenatore": tinfo.get("nu", ""),
            "gol_panchina": gol_panc,
            "assist_panchina": assist_panc,
            "totale_rimpianti": tot_rimpianti,
            "fantavoto_medio_panchina": avg_fv
        })

    classifica_rimpianti = sorted(classifica_rimpianti, key=lambda x: (x["gol_panchina"], x["assist_panchina"], x["totale_rimpianti"]), reverse=True)

    # 4. Classifica What-If
    standings_reale = {tid: {"punti": 0, "gf": 0, "gs": 0, "tot_fanta": 0.0, "v": 0, "p": 0, "s": 0} for tid in teams_map}
    standings_whatif = {tid: {"punti": 0, "gf": 0, "gs": 0, "tot_fanta": 0.0, "v": 0, "p": 0, "s": 0} for tid in teams_map}

    for turno in calendario:
        if not turno.get("calculated", False):
            continue
        g = turno["matchDay"]
        for m in turno.get("matches", []):
            hid, aid = m["tIdH"], m["tIdA"]
            
            # Reale
            standings_reale[hid]["punti"] += m["standingPtH"]
            standings_reale[aid]["punti"] += m["standingPtA"]
            res = m["result"].split("-")
            gh, ga = int(res[0]), int(res[1])
            standings_reale[hid]["gf"] += gh
            standings_reale[hid]["gs"] += ga
            standings_reale[aid]["gf"] += ga
            standings_reale[aid]["gs"] += gh
            standings_reale[hid]["tot_fanta"] += m["ptH"]
            standings_reale[aid]["tot_fanta"] += m["ptA"]
            if m["standingPtH"] == 3: standings_reale[hid]["v"] += 1; standings_reale[aid]["s"] += 1
            elif m["standingPtH"] == 1: standings_reale[hid]["p"] += 1; standings_reale[aid]["p"] += 1
            else: standings_reale[hid]["s"] += 1; standings_reale[aid]["v"] += 1

            # What-If
            b_h = best_scores.get((g, hid), m["ptH"])
            b_a = best_scores.get((g, aid), m["ptA"])
            w_gh = calcola_gol(b_h)
            w_ga = calcola_gol(b_a)

            if w_gh > w_ga:
                w_sp_h, w_sp_a = 3, 0
                standings_whatif[hid]["v"] += 1; standings_whatif[aid]["s"] += 1
            elif w_gh < w_ga:
                w_sp_h, w_sp_a = 0, 3
                standings_whatif[hid]["s"] += 1; standings_whatif[aid]["v"] += 1
            else:
                w_sp_h, w_sp_a = 1, 1
                standings_whatif[hid]["p"] += 1; standings_whatif[aid]["p"] += 1

            standings_whatif[hid]["punti"] += w_sp_h
            standings_whatif[aid]["punti"] += w_sp_a
            standings_whatif[hid]["gf"] += w_gh
            standings_whatif[hid]["gs"] += w_ga
            standings_whatif[aid]["gf"] += w_ga
            standings_whatif[aid]["gs"] += w_gh
            standings_whatif[hid]["tot_fanta"] += b_h
            standings_whatif[aid]["tot_fanta"] += b_a

    whatif_list = []
    for tid, tinfo in teams_map.items():
        r = standings_reale[tid]
        w = standings_whatif[tid]
        diff_pt = w["punti"] - r["punti"]
        whatif_list.append({
            "squadra": tinfo["n"],
            "allenatore": tinfo.get("nu", ""),
            "punti_reali": r["punti"],
            "punti_whatif": w["punti"],
            "diff_punti": diff_pt,
            "fanta_tot_reale": round(r["tot_fanta"], 1),
            "fanta_tot_whatif": round(w["tot_fanta"], 1),
            "gol_fatti_reali": r["gf"],
            "gol_fatti_whatif": w["gf"],
            "saldo_gol": w["gf"] - r["gf"],
            "stato_fortuna": "Fortunato 🍀" if diff_pt < 0 else ("Sfortunato 💥" if diff_pt > 0 else "In Parità ⚖️")
        })

    whatif_list = sorted(whatif_list, key=lambda x: (x["punti_whatif"], x["fanta_tot_whatif"]), reverse=True)

    # 5. Top Player per Squadra
    team_top_players = []
    for tid, tinfo in teams_map.items():
        tname = tinfo["n"]
        cal_ids = [int(x) for x in tinfo.get("cal", "").split(";") if x]
        cs_vals = [int(x) for x in tinfo.get("cs", "").split(";") if x]
        cost_map = dict(zip(cal_ids, cs_vals))

        roster_stats = []
        for pid in cal_ids:
            pinfo = players.get(pid, {})
            st = player_stats.get(pid, {'gol': 0, 'assist': 0, 'amm': 0, 'esp': 0, 'voti': [], 'fv': [], 'clean_sheet': 0})
            presenze = len(st['fv'])
            avg_fv = round(sum(st['fv'])/presenze, 2) if presenze > 0 else 0.0
            avg_voto = round(sum(st['voti'])/len(st['voti']), 2) if st['voti'] else 0.0
            costo = cost_map.get(pid, 1)
            roster_stats.append({
                "pid": pid,
                "nome": pinfo.get("name", f"ID {pid}"),
                "ruolo": RUOLI.get(pinfo.get("fcrle"), "?"),
                "ruolo_classe": RUOLI_CLASSE.get(pinfo.get("fcrle"), "badge-c"),
                "squadra_sa": pinfo.get("stnme", ""),
                "gol": st['gol'],
                "assist": st['assist'],
                "amm": st['amm'],
                "esp": st['esp'],
                "clean_sheet": st['clean_sheet'],
                "fantamedia": avg_fv,
                "media_voto": avg_voto,
                "presenze": presenze,
                "costo": costo
            })

        # Migliori di questa squadra
        bomber = sorted([p for p in roster_stats if p['gol'] > 0], key=lambda x: x['gol'], reverse=True)
        assistman = sorted([p for p in roster_stats if p['assist'] > 0], key=lambda x: x['assist'], reverse=True)
        badboy = sorted([p for p in roster_stats if (p['amm'] > 0 or p['esp'] > 0)], key=lambda x: (x['esp'], x['amm']), reverse=True)
        mvp = sorted([p for p in roster_stats if p['presenze'] >= 1], key=lambda x: x['fantamedia'], reverse=True)
        affari = sorted([p for p in roster_stats if p['costo'] <= 10 and p['presenze'] >= 1], key=lambda x: x['fantamedia'], reverse=True)

        team_top_players.append({
            "squadra": tname,
            "allenatore": tinfo.get("nu", ""),
            "mvp": mvp[0] if mvp else None,
            "bomber": bomber[0] if bomber else None,
            "assistman": assistman[0] if assistman else None,
            "badboy": badboy[0] if badboy else None,
            "affare": affari[0] if affari else None,
        })

    # 6. Leaderboard Individuale Assoluta di Lega
    tutti_calciatori = []
    for tid, tinfo in teams_map.items():
        tname = tinfo["n"]
        cal_ids = [int(x) for x in tinfo.get("cal", "").split(";") if x]
        for pid in cal_ids:
            pinfo = players.get(pid, {})
            st = player_stats.get(pid, {'gol': 0, 'assist': 0, 'amm': 0, 'esp': 0, 'voti': [], 'fv': [], 'clean_sheet': 0})
            if st['gol'] > 0 or st['assist'] > 0 or st['amm'] > 0 or st['esp'] > 0 or len(st['fv']) > 0:
                presenze = len(st['fv'])
                avg_fv = round(sum(st['fv'])/presenze, 2) if presenze > 0 else 0.0
                tutti_calciatori.append({
                    "nome": pinfo.get("name", f"ID {pid}"),
                    "ruolo": RUOLI.get(pinfo.get("fcrle"), "?"),
                    "ruolo_classe": RUOLI_CLASSE.get(pinfo.get("fcrle"), "badge-c"),
                    "squadra_fanta": tname,
                    "squadra_sa": pinfo.get("stnme", ""),
                    "gol": st['gol'],
                    "assist": st['assist'],
                    "amm": st['amm'],
                    "esp": st['esp'],
                    "fantamedia": avg_fv,
                    "presenze": presenze
                })

    top_marcatori = sorted([p for p in tutti_calciatori if p['gol'] > 0], key=lambda x: x['gol'], reverse=True)[:10]
    top_assist = sorted([p for p in tutti_calciatori if p['assist'] > 0], key=lambda x: x['assist'], reverse=True)[:10]
    top_cattivi = sorted([p for p in tutti_calciatori if p['amm'] > 0 or p['esp'] > 0], key=lambda x: (x['esp'], x['amm']), reverse=True)[:10]

    # 7. Moduli
    moduli_list = []
    for mod, s in moduli_stats.items():
        media_punti = round(s["tot_punti"] / s["usato"], 2) if s["usato"] > 0 else 0
        moduli_list.append({
            "modulo": mod,
            "usato": s["usato"],
            "media_punti": media_punti,
            "vittorie": s["vittorie"],
            "pareggi": s["pareggi"],
            "sconfitte": s["sconfitte"],
            "win_rate": round((s["vittorie"] / s["usato"]) * 100, 1) if s["usato"] > 0 else 0
        })
    moduli_list = sorted(moduli_list, key=lambda x: x["media_punti"], reverse=True)

    # 8. Rose e Finanze
    rose_data = []
    for tid, tinfo in teams_map.items():
        cal_ids = [int(x) for x in tinfo.get("cal", "").split(";") if x]
        cs_vals = [int(x) for x in tinfo.get("cs", "").split(";") if x]
        giocatori_rosa = []
        for pid, costo in zip(cal_ids, cs_vals):
            pinfo = players.get(pid, {})
            giocatori_rosa.append({
                "nome": pinfo.get("name", f"ID {pid}"),
                "ruolo": RUOLI.get(pinfo.get("fcrle"), "?"),
                "ruolo_classe": RUOLI_CLASSE.get(pinfo.get("fcrle"), "badge-c"),
                "squadra_sa": pinfo.get("stnme", ""),
                "costo": costo,
                "quotazione": pinfo.get("quotd", 0),
                "fantamedia": pinfo.get("fagrd", 0.0)
            })
        giocatori_rosa = sorted(giocatori_rosa, key=lambda x: x["costo"], reverse=True)
        rose_data.append({
            "squadra": tinfo.get("n"),
            "allenatore": tinfo.get("nu"),
            "crediti_spesi": tinfo.get("crs", 0),
            "crediti_residui": tinfo.get("cr", 0),
            "top_player": giocatori_rosa[0]["nome"] if giocatori_rosa else "N/D",
            "top_costo": giocatori_rosa[0]["costo"] if giocatori_rosa else 0,
            "rosa": giocatori_rosa
        })

    # Dati unificati
    app_data = {
        "classifica_rimpianti": classifica_rimpianti,
        "classifica_whatif": whatif_list,
        "team_top_players": team_top_players,
        "top_marcatori": top_marcatori,
        "top_assist": top_assist,
        "top_cattivi": top_cattivi,
        "giornate": giornate_data,
        "moduli": moduli_list,
        "rose": rose_data,
        "status": status_data
    }

    # Generazione HTML moderno
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>El Figuerao - FantaStats & Rimpianti Panchina</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #0a0d14;
      --bg-surface: #121722;
      --bg-card: #181f2f;
      --bg-card-hover: #1f273b;
      --primary: #6366f1;
      --primary-light: #818cf8;
      --accent-gold: #f59e0b;
      --accent-red: #ef4444;
      --accent-green: #10b981;
      --accent-cyan: #06b6d4;
      --accent-purple: #a855f7;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --border: #222d42;
      --border-glow: rgba(99, 102, 241, 0.25);
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --shadow-card: 0 10px 25px -5px rgba(0, 0, 0, 0.45);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: radial-gradient(circle at top center, #171d2f 0%, #0a0d14 100%);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      line-height: 1.5;
      padding-bottom: 60px;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 20px;
    }}

    /* HEADER */
    header {{
      padding: 30px 0 20px;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      background: rgba(10, 13, 20, 0.88);
      backdrop-filter: blur(16px);
      z-index: 100;
    }}
    .header-content {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 15px;
    }}
    .logo-area h1 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.8rem;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #fff 30%, var(--primary-light) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .tagline {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 3px;
    }}
    .badge-status {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.12);
      color: var(--accent-green);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .badge-status::before {{
      content: '';
      width: 7px;
      height: 7px;
      background: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--accent-green);
    }}

    .btn-share {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: linear-gradient(135deg, #25D366, #128C7E);
      color: #fff;
      border: none;
      padding: 10px 18px;
      border-radius: var(--radius-sm);
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(37, 211, 102, 0.3);
      transition: all 0.25s ease;
    }}
    .btn-share:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(37, 211, 102, 0.45);
    }}

    /* TABS NAV */
    .tabs-nav {{
      display: flex;
      gap: 10px;
      margin: 25px 0;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      overflow-x: auto;
    }}
    .tab-btn {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      font-family: inherit;
      font-weight: 600;
      font-size: 0.95rem;
      padding: 10px 18px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.04);
    }}
    .tab-btn.active {{
      color: #fff;
      background: var(--primary);
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }}

    /* TAB PANELS */
    .tab-pane {{
      display: none;
      animation: fadeIn 0.3s ease;
    }}
    .tab-pane.active {{
      display: block;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* HERO STATS CARDS */
    .hero-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 16px;
      margin-bottom: 25px;
    }}
    .hero-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 20px;
      position: relative;
      overflow: hidden;
    }}
    .hero-card::after {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
      background: var(--primary);
    }}
    .hero-card.gold::after {{ background: var(--accent-gold); }}
    .hero-card.red::after {{ background: var(--accent-red); }}
    .hero-card.green::after {{ background: var(--accent-green); }}
    .hero-card.purple::after {{ background: var(--accent-purple); }}

    .hero-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}
    .hero-val {{
      font-size: 1.8rem;
      font-weight: 800;
      font-family: 'Space Grotesk', sans-serif;
      margin-top: 6px;
      color: #fff;
    }}
    .hero-sub {{
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* TABLES */
    .table-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      overflow: hidden;
      box-shadow: var(--shadow-card);
      margin-bottom: 30px;
    }}
    .table-header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(255, 255, 255, 0.015);
    }}
    .table-header h2 {{
      font-size: 1.15rem;
      font-family: 'Space Grotesk', sans-serif;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}
    th {{
      background: rgba(10, 13, 20, 0.6);
      color: var(--text-muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.6px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--border);
    }}
    td {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      font-size: 0.92rem;
    }}
    tbody tr:hover {{
      background: var(--bg-card-hover);
    }}
    tbody tr:last-child td {{
      border-bottom: none;
    }}

    .rank-cell {{
      font-weight: 800;
      font-size: 1rem;
      width: 45px;
      color: var(--text-muted);
    }}
    .rank-1 {{ color: #fbbf24; font-size: 1.3rem; }}
    .rank-2 {{ color: #94a3b8; font-size: 1.15rem; }}
    .rank-3 {{ color: #b45309; font-size: 1.05rem; }}

    .team-cell {{
      font-weight: 700;
      color: #fff;
    }}
    .coach-name {{
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .stat-badge {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.88rem;
    }}
    .badge-gol {{
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    .badge-assist {{
      background: rgba(6, 182, 212, 0.15);
      color: #22d3ee;
      border: 1px solid rgba(6, 182, 212, 0.3);
    }}
    .badge-fv {{
      background: rgba(99, 102, 241, 0.15);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.3);
    }}
    .badge-card {{
      background: rgba(245, 158, 11, 0.15);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .diff-plus {{
      color: var(--accent-green);
      font-weight: 800;
    }}
    .diff-minus {{
      color: var(--accent-red);
      font-weight: 800;
    }}
    .diff-zero {{
      color: var(--text-muted);
      font-weight: 700;
    }}

    /* RUOLI BADGES */
    .badge-role {{
      display: inline-block;
      width: 24px;
      height: 24px;
      line-height: 24px;
      text-align: center;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 800;
      margin-right: 6px;
    }}
    .badge-p {{ background: #eab308; color: #000; }}
    .badge-d {{ background: #10b981; color: #000; }}
    .badge-c {{ background: #3b82f6; color: #fff; }}
    .badge-a {{ background: #ef4444; color: #fff; }}

    /* CARDS ROUNDS */
    .round-selector {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
    }}
    .round-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      font-family: inherit;
      padding: 8px 16px;
      border-radius: var(--radius-sm);
      font-size: 0.88rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .round-btn.active {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }}

    .regrets-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }}
    .regret-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.2s, border-color 0.2s;
    }}
    .regret-card:hover {{
      transform: translateY(-2px);
      border-color: var(--primary-light);
    }}
    .regret-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    .regret-player-name {{
      font-size: 1.05rem;
      font-weight: 700;
      color: #fff;
    }}
    .regret-team {{
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .regret-fv-box {{
      text-align: right;
    }}
    .regret-fv-val {{
      font-size: 1.45rem;
      font-weight: 800;
      font-family: 'Space Grotesk', sans-serif;
      color: #a5b4fc;
    }}
    .regret-voto-puro {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}
    .regret-badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }}

    /* TEAM CARDS FOR TOP PLAYERS */
    .teams-top-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }}
    .team-top-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 20px;
      box-shadow: var(--shadow-card);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .team-top-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;
    }}
    .team-top-title {{
      font-size: 1.15rem;
      font-weight: 800;
      color: #fff;
    }}
    .team-top-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.88rem;
      padding: 6px 0;
      border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
    }}
    .team-top-row:last-child {{
      border-bottom: none;
    }}
    .top-category {{
      color: var(--text-muted);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .top-player-val {{
      font-weight: 700;
      color: #fff;
      text-align: right;
    }}

    /* LEADERBOARD 3 COLS */
    .leader-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }}

    /* TOAST */
    .toast {{
      position: fixed;
      bottom: 25px;
      right: 25px;
      background: #10b981;
      color: #fff;
      padding: 12px 20px;
      border-radius: var(--radius-sm);
      font-weight: 700;
      font-size: 0.9rem;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      display: none;
      z-index: 1000;
    }}

    @media (max-width: 768px) {{
      .header-content {{ flex-direction: column; align-items: flex-start; }}
      th, td {{ padding: 12px 14px; }}
    }}
  </style>
</head>
<body>

  <header>
    <div class="container header-content">
      <div class="logo-area">
        <h1>⚽ El Figuerao <span>Stats</span></h1>
        <div class="tagline">Lega Fantacalcio (ID: 619614) • Analisi Statistiche, What-If & Top Players</div>
      </div>
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="badge-status">Giornata 2 Calcolata</span>
        <button class="btn-share" onclick="condividiWhatsApp()">
          <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
          Condividi Report WhatsApp
        </button>
      </div>
    </div>
  </header>

  <main class="container">

    <!-- HERO CARDS -->
    <div class="hero-grid" style="margin-top: 25px;">
      <div class="hero-card red">
        <div class="hero-label">Re dei Rimpianti ⚽</div>
        <div class="hero-val" id="top-team-regret">-</div>
        <div class="hero-sub" id="top-team-regret-sub">-</div>
      </div>
      <div class="hero-card purple">
        <div class="hero-label">Punti Rubati alla Sorte 🔮</div>
        <div class="hero-val" id="top-whatif-lucky">-</div>
        <div class="hero-sub" id="top-whatif-lucky-sub">-</div>
      </div>
      <div class="hero-card gold">
        <div class="hero-label">Più Penalizzato dalla Panchina 💥</div>
        <div class="hero-val" id="top-whatif-unlucky">-</div>
        <div class="hero-sub" id="top-whatif-unlucky-sub">-</div>
      </div>
      <div class="hero-card green">
        <div class="hero-label">Top Bonus Singolo in Panchina</div>
        <div class="hero-val" id="top-single-bonus">-</div>
        <div class="hero-sub" id="top-single-bonus-sub">-</div>
      </div>
    </div>

    <!-- TABS -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('tab-whatif')">🔮 Classifica What-If</button>
      <button class="tab-btn" onclick="switchTab('tab-rimpianti')">🏆 Rimpianti Panchina</button>
      <button class="tab-btn" onclick="switchTab('tab-topplayers')">🌟 Top Player per Squadra</button>
      <button class="tab-btn" onclick="switchTab('tab-leaderboards')">🥇 Leaderboard Assoluta</button>
      <button class="tab-btn" onclick="switchTab('tab-giornate')">📅 Dettaglio Turni</button>
      <button class="tab-btn" onclick="switchTab('tab-moduli')">📐 Moduli Tattici</button>
      <button class="tab-btn" onclick="switchTab('tab-rose')">💼 Rose & Budget</button>
    </div>

    <!-- TAB 1: CLASSIFICA WHAT-IF -->
    <div id="tab-whatif" class="tab-pane active">
      <div class="table-card">
        <div class="table-header">
          <div>
            <h2>Classifica Reale vs Classifica "What-If" (Senza Rimpianti)</h2>
            <span style="font-size: 0.85rem; color: var(--text-muted);">Cosa sarebbe successo se ogni squadra avesse schierato la sua formazione ottimale?</span>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th style="width: 50px;">Pos</th>
              <th>Fantasquadra</th>
              <th>Pt Reali</th>
              <th>Pt What-If</th>
              <th>Differenza</th>
              <th>FantaTot Reale</th>
              <th>FantaTot What-If</th>
              <th>Gol Reali vs What-If</th>
              <th>Esito Sorte</th>
            </tr>
          </thead>
          <tbody id="tbody-whatif"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: CLASSIFICA RIMPIANTI -->
    <div id="tab-rimpianti" class="tab-pane">
      <div class="table-card">
        <div class="table-header">
          <h2>Classifica Generale Bonus Sprecati in Panchina</h2>
          <span style="font-size: 0.85rem; color: var(--text-muted);">Calciatori con Gol, Assist o Fantavoto &ge; 7.0 rimasti fuori</span>
        </div>
        <table>
          <thead>
            <tr>
              <th style="width: 50px;">Pos</th>
              <th>Fantasquadra</th>
              <th>Gol in Panchina ⚽</th>
              <th>Assist in Panchina 👟</th>
              <th>Totale Rimpianti</th>
              <th>FantaMedia Panchina</th>
            </tr>
          </thead>
          <tbody id="tbody-classifica-rimpianti"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: TOP PLAYER PER SQUADRA -->
    <div id="tab-topplayers" class="tab-pane">
      <div style="margin-bottom: 20px;">
        <h2>🌟 I Protagonisti di Ciascuna Rosa</h2>
        <p style="font-size: 0.88rem; color: var(--text-muted); margin-top: 4px;">MVP, Capocannoniere, Assistman, Mister Cartellino e Miglior Affare interno per squadra.</p>
      </div>
      <div class="teams-top-grid" id="teams-top-container"></div>
    </div>

    <!-- TAB 4: LEADERBOARD ASSOLUTA -->
    <div id="tab-leaderboards" class="tab-pane">
      <div class="leader-grid">
        <!-- Marcatori -->
        <div class="table-card">
          <div class="table-header">
            <h2>⚽ Classifica Marcatori</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Giocatore</th>
                <th>Squadra Fanta</th>
                <th style="text-align: right;">Gol</th>
              </tr>
            </thead>
            <tbody id="tbody-top-marcatori"></tbody>
          </table>
        </div>

        <!-- Assist -->
        <div class="table-card">
          <div class="table-header">
            <h2>👟 Classifica Assist</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Giocatore</th>
                <th>Squadra Fanta</th>
                <th style="text-align: right;">Assist</th>
              </tr>
            </thead>
            <tbody id="tbody-top-assist"></tbody>
          </table>
        </div>

        <!-- Cartellini -->
        <div class="table-card">
          <div class="table-header">
            <h2>🟨 Mister Cartellino (Cattivi)</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Giocatore</th>
                <th>Squadra Fanta</th>
                <th style="text-align: right;">🟨 / 🟥</th>
              </tr>
            </thead>
            <tbody id="tbody-top-cattivi"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 5: DETTAGLIO GIORNATE -->
    <div id="tab-giornate" class="tab-pane">
      <div class="round-selector" id="round-buttons"></div>
      <div class="regrets-grid" id="regrets-container"></div>
    </div>

    <!-- TAB 6: MODULI TATTICI -->
    <div id="tab-moduli" class="tab-pane">
      <div class="table-card">
        <div class="table-header">
          <h2>Rendimento per Modulo Schierato</h2>
          <span style="font-size: 0.85rem; color: var(--text-muted);">Quale modulo porta più punti alla lunga?</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Modulo</th>
              <th>Volte Schierato</th>
              <th>Media Punti Fantasquadra</th>
              <th>Vittorie</th>
              <th>Pareggi</th>
              <th>Sconfitte</th>
              <th>Win Rate</th>
            </tr>
          </thead>
          <tbody id="tbody-moduli"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 7: ROSE & BUDGET -->
    <div id="tab-rose" class="tab-pane">
      <div class="table-card">
        <div class="table-header">
          <h2>Situazione Finanziaria e Top Spese Rose</h2>
          <span style="font-size: 0.85rem; color: var(--text-muted);">Crediti spesi e residui (Budget 500)</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Squadra</th>
              <th>Allenatore</th>
              <th>Crediti Spesi</th>
              <th>Crediti Residui</th>
              <th>Top Player Acquistato</th>
              <th>Costo Top Player</th>
            </tr>
          </thead>
          <tbody id="tbody-rose"></tbody>
        </table>
      </div>
    </div>

  </main>

  <div id="toast" class="toast">Testo copiato negli appunti! Incollalo su WhatsApp 🚀</div>

  <script>
    const data = {json.dumps(app_data, ensure_ascii=False)};

    document.addEventListener("DOMContentLoaded", () => {{
      renderHero();
      renderWhatIf();
      renderClassificaRimpianti();
      renderTeamTopPlayers();
      renderLeaderboards();
      renderRounds();
      renderModuli();
      renderRose();
    }});

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }}

    function renderHero() {{
      const c = data.classifica_rimpianti;
      if (c.length > 0) {{
        document.getElementById('top-team-regret').innerText = c[0].squadra;
        document.getElementById('top-team-regret-sub').innerText = `${{c[0].gol_panchina}} gol persi in panchina`;
      }}

      // What-If sfortunato & fortunato
      const wSorted = [...data.classifica_whatif].sort((a, b) => b.diff_punti - a.diff_punti);
      const unlucky = wSorted[0];
      const lucky = wSorted[wSorted.length - 1];

      if (unlucky) {{
        document.getElementById('top-whatif-unlucky').innerText = unlucky.squadra;
        document.getElementById('top-whatif-unlucky-sub').innerText = `${{unlucky.diff_punti > 0 ? '+' : ''}}${{unlucky.diff_punti}} pt persi con scelte errate`;
      }}

      if (lucky) {{
        document.getElementById('top-whatif-lucky').innerText = lucky.squadra;
        document.getElementById('top-whatif-lucky-sub').innerText = `${{lucky.diff_punti}} pt guadagnati per errori avversari`;
      }}

      // Miglior singolo bonus
      let maxFv = 0;
      let maxPlayer = "";
      let maxTeam = "";
      data.giornate.forEach(g => {{
        g.squadre.forEach(s => {{
          s.rimpianti.forEach(r => {{
            if (r.fantavoto > maxFv) {{
              maxFv = r.fantavoto;
              maxPlayer = r.nome;
              maxTeam = s.nome;
            }}
          }});
        }});
      }});
      document.getElementById('top-single-bonus').innerText = `${{maxPlayer}} (${{maxFv}})`;
      document.getElementById('top-single-bonus-sub').innerText = `in panchina con ${{maxTeam}}`;
    }}

    function renderWhatIf() {{
      const tbody = document.getElementById('tbody-whatif');
      tbody.innerHTML = "";
      data.classifica_whatif.forEach((item, idx) => {{
        const rankClass = idx === 0 ? "rank-1" : idx === 1 ? "rank-2" : idx === 2 ? "rank-3" : "";
        const rankIcon = idx === 0 ? "🥇" : idx === 1 ? "🥈" : idx === 2 ? "🥉" : (idx + 1);
        const diffClass = item.diff_punti > 0 ? "diff-plus" : item.diff_punti < 0 ? "diff-minus" : "diff-zero";
        const diffText = item.diff_punti > 0 ? `+${{item.diff_punti}} pt 💥` : item.diff_punti < 0 ? `${{item.diff_punti}} pt 🍀` : `0 pt ⚖️`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="rank-cell ${{rankClass}}">${{rankIcon}}</td>
          <td>
            <div class="team-cell">${{item.squadra}}</div>
            <div class="coach-name">${{item.allenatore}}</div>
          </td>
          <td><b>${{item.punti_reali}}</b></td>
          <td><span class="stat-badge badge-fv">${{item.punti_whatif}} pt</span></td>
          <td class="${{diffClass}}">${{diffText}}</td>
          <td>${{item.fanta_tot_reale}}</td>
          <td><b>${{item.fanta_tot_whatif}}</b></td>
          <td>${{item.gol_fatti_reali}} ➔ <b>${{item.gol_fatti_whatif}}</b></td>
          <td><span style="font-weight: 700; font-size: 0.85rem;">${{item.stato_fortuna}}</span></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function renderClassificaRimpianti() {{
      const tbody = document.getElementById('tbody-classifica-rimpianti');
      tbody.innerHTML = "";
      data.classifica_rimpianti.forEach((item, idx) => {{
        const rankClass = idx === 0 ? "rank-1" : idx === 1 ? "rank-2" : idx === 2 ? "rank-3" : "";
        const rankIcon = idx === 0 ? "🥇" : idx === 1 ? "🥈" : idx === 2 ? "🥉" : (idx + 1);
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="rank-cell ${{rankClass}}">${{rankIcon}}</td>
          <td>
            <div class="team-cell">${{item.squadra}}</div>
            <div class="coach-name">${{item.allenatore}}</div>
          </td>
          <td><span class="stat-badge badge-gol">${{item.gol_panchina}} Gol ⚽</span></td>
          <td><span class="stat-badge badge-assist">${{item.assist_panchina}} Assist 👟</span></td>
          <td><b>${{item.totale_rimpianti}}</b> giocatori</td>
          <td><span class="stat-badge badge-fv">${{item.fantavoto_medio_panchina}} FM</span></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function renderTeamTopPlayers() {{
      const container = document.getElementById('teams-top-container');
      container.innerHTML = "";
      data.team_top_players.forEach(t => {{
        const card = document.createElement('div');
        card.className = "team-top-card";
        
        let mvpStr = t.mvp ? `<span class="badge-role ${{t.mvp.ruolo_classe}}">${{t.mvp.ruolo}}</span>${{t.mvp.nome}} (${{t.mvp.fantamedia}} FM)` : "Nessuno a voto";
        let bomberStr = t.bomber ? `<span class="badge-role ${{t.bomber.ruolo_classe}}">${{t.bomber.ruolo}}</span>${{t.bomber.nome}} (${{t.bomber.gol}} ⚽)` : "Nessun gol";
        let assistStr = t.assistman ? `<span class="badge-role ${{t.assistman.ruolo_classe}}">${{t.assistman.ruolo}}</span>${{t.assistman.nome}} (${{t.assistman.assist}} 👟)` : "Nessun assist";
        let badboyStr = t.badboy ? `<span class="badge-role ${{t.badboy.ruolo_classe}}">${{t.badboy.ruolo}}</span>${{t.badboy.nome}} (${{t.badboy.amm}} 🟨 ${{t.badboy.esp ? t.badboy.esp + ' 🟥' : ''}})` : "Tutti puliti";
        let affareStr = t.affare ? `<span class="badge-role ${{t.affare.ruolo_classe}}">${{t.affare.ruolo}}</span>${{t.affare.nome}} (${{t.affare.fantamedia}} FM @ ${{t.affare.costo}} cr)` : "N/D";

        card.innerHTML = `
          <div class="team-top-header">
            <div>
              <div class="team-top-title">${{t.squadra}}</div>
              <div class="coach-name">All: ${{t.allenatore}}</div>
            </div>
          </div>
          <div>
            <div class="team-top-row">
              <span class="top-category">👑 MVP Squadra:</span>
              <span class="top-player-val">${{mvpStr}}</span>
            </div>
            <div class="team-top-row">
              <span class="top-category">⚽ Capocannoniere:</span>
              <span class="top-player-val">${{bomberStr}}</span>
            </div>
            <div class="team-top-row">
              <span class="top-category">👟 Assist-man:</span>
              <span class="top-player-val">${{assistStr}}</span>
            </div>
            <div class="team-top-row">
              <span class="top-category">🟨 Mister Cartellino:</span>
              <span class="top-player-val">${{badboyStr}}</span>
            </div>
            <div class="team-top-row">
              <span class="top-category">💎 Top Affare Low Cost:</span>
              <span class="top-player-val">${{affareStr}}</span>
            </div>
          </div>
        `;
        container.appendChild(card);
      }});
    }}

    function renderLeaderboards() {{
      // Marcatori
      const tbodyMarcatori = document.getElementById('tbody-top-marcatori');
      tbodyMarcatori.innerHTML = "";
      data.top_marcatori.forEach(p => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="badge-role ${{p.ruolo_classe}}">${{p.ruolo}}</span><b>${{p.nome}}</b> <span style="font-size:0.78rem; color:var(--text-muted);">(${{p.squadra_sa}})</span></td>
          <td style="font-size: 0.85rem; color: var(--text-muted);">${{p.squadra_fanta}}</td>
          <td style="text-align: right;"><span class="stat-badge badge-gol">${{p.gol}} ⚽</span></td>
        `;
        tbodyMarcatori.appendChild(tr);
      }});

      // Assist
      const tbodyAssist = document.getElementById('tbody-top-assist');
      tbodyAssist.innerHTML = "";
      data.top_assist.forEach(p => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="badge-role ${{p.ruolo_classe}}">${{p.ruolo}}</span><b>${{p.nome}}</b> <span style="font-size:0.78rem; color:var(--text-muted);">(${{p.squadra_sa}})</span></td>
          <td style="font-size: 0.85rem; color: var(--text-muted);">${{p.squadra_fanta}}</td>
          <td style="text-align: right;"><span class="stat-badge badge-assist">${{p.assist}} 👟</span></td>
        `;
        tbodyAssist.appendChild(tr);
      }});

      // Cattivi
      const tbodyCattivi = document.getElementById('tbody-top-cattivi');
      tbodyCattivi.innerHTML = "";
      data.top_cattivi.forEach(p => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="badge-role ${{p.ruolo_classe}}">${{p.ruolo}}</span><b>${{p.nome}}</b> <span style="font-size:0.78rem; color:var(--text-muted);">(${{p.squadra_sa}})</span></td>
          <td style="font-size: 0.85rem; color: var(--text-muted);">${{p.squadra_fanta}}</td>
          <td style="text-align: right;"><span class="stat-badge badge-card">${{p.amm}} 🟨 ${{p.esp ? p.esp + ' 🟥' : ''}}</span></td>
        `;
        tbodyCattivi.appendChild(tr);
      }});
    }}

    let currentSelectedRound = 2;

    function renderRounds() {{
      const btnContainer = document.getElementById('round-buttons');
      btnContainer.innerHTML = "";
      data.giornate.forEach(g => {{
        const btn = document.createElement('button');
        btn.className = `round-btn ${{g.giornata === currentSelectedRound ? 'active' : ''}}`;
        btn.innerText = `Giornata ${{g.giornata}}`;
        btn.onclick = () => {{
          currentSelectedRound = g.giornata;
          document.querySelectorAll('.round-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          renderRegretsGrid(g.giornata);
        }};
        btnContainer.appendChild(btn);
      }});
      renderRegretsGrid(currentSelectedRound);
    }}

    function renderRegretsGrid(roundNum) {{
      const container = document.getElementById('regrets-container');
      container.innerHTML = "";
      const g = data.giornate.find(x => x.giornata === roundNum);
      if (!g) return;

      let allRegrets = [];
      g.squadre.forEach(s => {{
        s.rimpianti.forEach(r => {{
          allRegrets.push({{ ...r, squadra: s.nome }});
        }});
      }});

      allRegrets.sort((a, b) => b.fantavoto - a.fantavoto);

      if (allRegrets.length === 0) {{
        container.innerHTML = "<div style='color: var(--text-muted);'>Nessun rimpianto clamoroso per questo turno!</div>";
        return;
      }}

      allRegrets.forEach(r => {{
        const card = document.createElement('div');
        card.className = "regret-card";
        let badgesHtml = "";
        if (r.gol > 0) badgesHtml += `<span class="stat-badge badge-gol">${{r.gol}} Gol ⚽</span>`;
        if (r.assist > 0) badgesHtml += `<span class="stat-badge badge-assist">${{r.assist}} Assist 👟</span>`;
        if (r.clean_sheet > 0) badgesHtml += `<span class="stat-badge badge-assist">Clean Sheet 🧤</span>`;
        if (r.fantavoto >= 7.0 && r.gol === 0 && r.assist === 0) badgesHtml += `<span class="stat-badge badge-fv">Voto Alto ⭐</span>`;

        card.innerHTML = `
          <div>
            <div class="regret-card-top">
              <div>
                <div class="regret-player-name">
                  <span class="badge-role ${{r.ruolo_classe}}">${{r.ruolo}}</span>
                  ${{r.nome}} <span style="font-size: 0.8rem; color: var(--text-muted);">(${{r.squadra_serie_a}})</span>
                </div>
                <div class="regret-team">in panchina con <b>${{r.squadra}}</b></div>
              </div>
              <div class="regret-fv-box">
                <div class="regret-fv-val">${{r.fantavoto}}</div>
                <div class="regret-voto-puro">Voto puro: ${{r.voto}}</div>
              </div>
            </div>
          </div>
          <div class="regret-badges">
            ${{badgesHtml}}
          </div>
        `;
        container.appendChild(card);
      }});
    }}

    function renderModuli() {{
      const tbody = document.getElementById('tbody-moduli');
      tbody.innerHTML = "";
      data.moduli.forEach(m => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><b>${{m.modulo}}</b></td>
          <td>${{m.usato}} volte</td>
          <td><span class="stat-badge badge-fv">${{m.media_punti}} pt</span></td>
          <td style="color: var(--accent-green); font-weight: 700;">${{m.vittorie}}</td>
          <td style="color: var(--text-muted); font-weight: 700;">${{m.pareggi}}</td>
          <td style="color: var(--accent-red); font-weight: 700;">${{m.sconfitte}}</td>
          <td><b>${{m.win_rate}}%</b></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function renderRose() {{
      const tbody = document.getElementById('tbody-rose');
      tbody.innerHTML = "";
      data.rose.forEach(r => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="team-cell">${{r.squadra}}</td>
          <td class="coach-name">${{r.allenatore}}</td>
          <td>${{r.crediti_spesi}} / 500</td>
          <td style="color: var(--accent-green); font-weight: 700;">${{r.crediti_residui}} cr</td>
          <td><b>${{r.top_player}}</b></td>
          <td><span class="stat-badge badge-fv">${{r.top_costo}} cr</span></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function condividiWhatsApp() {{
      const topTeam = data.classifica_rimpianti[0];
      const wSorted = [...data.classifica_whatif].sort((a, b) => b.diff_punti - a.diff_punti);
      const unlucky = wSorted[0];
      const lucky = wSorted[wSorted.length - 1];

      let msg = `🚨 *FANTASTATS: REPORT COMPLETO GIORNATA 2* 🚨\\n`;
      msg += `🏆 *Lega El Figuerao*\\n\\n`;
      msg += `👑 *Re dei Rimpianti:* ${{topTeam.squadra}} (${{topTeam.gol_panchina}} GOL persi!)\\n`;
      if (unlucky && unlucky.diff_punti > 0) {{
        msg += `💥 *Il più Penalizzato dalla Panchina:* ${{unlucky.squadra}} (sarebbe a ${{unlucky.punti_whatif}} pt invece di ${{unlucky.punti_reali}}!)\\n`;
      }}
      if (lucky && lucky.diff_punti < 0) {{
        msg += `🍀 *Il Baciato dalla Fortuna:* ${{lucky.squadra}} (+${{Math.abs(lucky.diff_punti)}} pt guadagnati per errori altrui)\\n`;
      }}
      msg += `\\n📊 *CLASSIFICA WHAT-IF (Punti Potenziali):*\\n`;
      data.classifica_whatif.slice(0, 5).forEach((t, i) => {{
        const diffStr = t.diff_punti > 0 ? `(+${{t.diff_punti}})` : (t.diff_punti < 0 ? `(${{t.diff_punti}})` : `(=)`);
        msg += `${{i+1}}. ${{t.squadra}}: ${{t.punti_whatif}} pt ${{diffStr}}\\n`;
      }});
      msg += `\\n👉 Apri la dashboard online per vedere tutti i Top Player, Assist e Cartellini!`;

      navigator.clipboard.writeText(msg).then(() => {{
        const toast = document.getElementById('toast');
        toast.style.display = 'block';
        setTimeout(() => {{ toast.style.display = 'none'; }}, 3000);
      }});

      const waUrl = "https://api.whatsapp.com/send?text=" + encodeURIComponent(msg);
      window.open(waUrl, '_blank');
    }}
  </script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("SUCCESS: Generato index.html aggiornato con What-If e Top Players!")

if __name__ == "__main__":
    genera_sito()

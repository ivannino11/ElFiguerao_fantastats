import json
import pandas as pd
from fanta_utils import giocatori_entrati, formazione_effettiva, panchina_effettiva, ha_voto

with open("calendario.json", "r", encoding="utf-8") as f:
    calendario = json.load(f)

with open("squadre_fanta.json", "r", encoding="utf-8") as f:
    teams = {t["id"]: t["n"] for t in json.load(f)["data"]}

with open("giocatori_rose.json", "r", encoding="utf-8") as f:
    players = {p["id"]: p for p in json.load(f)["players"]}

RUOLI = {1: "P", 2: "D", 3: "C", 4: "A"}

def calcola_gol(pt):
    if pt < 66.0:
        return 0
    return int((pt - 66.0) // 6) + 1

# Calcola Best XI per ogni squadra in ogni giornata
best_scores = {} # (giornata, tid) -> best_tot

for g in [1, 2]:
    with open(f"lineup_giornata_{g}.json", "r", encoding="utf-8") as f:
        lineup = json.load(f)
    for t in lineup:
        tid = t["tid"]
        tot_reale = t.get("tot", 0)
        
        # Raccogliamo tutti i giocatori a voto (titolari + panchinari effettivi)
        # Per semplicità e massima coerenza tattica:
        # Per ogni ruolo (P, D, C, A), possiamo sostituire i peggiori titolari con i migliori panchinari dello stesso ruolo se hanno fantavoto superiore
        starters = t.get("starts", [])
        bench = t.get("bench", [])
        
        # Sostituzioni realmente avvenute: campo ptype ('U' uscito, 'E' entrato).
        # Gestisce tutte le sostituzioni, non solo la prima. swtc è la regola tattica, non i cambi.
        sub_in = giocatori_entrati(t)
        in_campo = formazione_effettiva(t)  # titolari non usciti + entrati
        fuori = panchina_effettiva(t)        # panchinari rimasti fuori

        # Giocatori titolari finali effettivi
        # Un titolare ha cscr valido (se s.v. ed è uscito, è stato sostituito)
        delta_max = 0.0
        # Mappiamo i ruoli
        for role_id, role_code in RUOLI.items():
            st_role = [p for p in in_campo if players.get(p["pid"], {}).get("fcrle") == role_id and ha_voto(p)]
            bn_role = [p for p in fuori if players.get(p["pid"], {}).get("fcrle") == role_id and ha_voto(p)]
            
            st_sorted = sorted(st_role, key=lambda x: x["cscr"]) # peggiori prima
            bn_sorted = sorted(bn_role, key=lambda x: x["cscr"], reverse=True) # migliori prima
            
            for s_bad, b_good in zip(st_sorted, bn_sorted):
                if b_good["cscr"] > s_bad["cscr"]:
                    delta_max += (b_good["cscr"] - s_bad["cscr"])
        
        best_tot = round(tot_reale + delta_max, 1)
        best_scores[(g, tid)] = best_tot

print("Best Scores calcolati con successo!")
for (g, tid), b_tot in list(best_scores.items())[:5]:
    print(f"G{g} {teams[tid]}: Best {b_tot}")

# Ora calcoliamo la Classifica What-If
classifica_reale = {tid: {"nome": name, "punti": 0, "gf": 0, "gs": 0, "tot": 0.0} for tid, name in teams.items()}
classifica_whatif = {tid: {"nome": name, "punti": 0, "gf": 0, "gs": 0, "tot": 0.0} for tid, name in teams.items()}

for turno in calendario[:2]:
    g = turno["matchDay"]
    for m in turno.get("matches", []):
        hid, aid = m["tIdH"], m["tIdA"]
        
        # Reale
        classifica_reale[hid]["punti"] += m["standingPtH"]
        classifica_reale[aid]["punti"] += m["standingPtA"]
        res = m["result"].split("-")
        classifica_reale[hid]["gf"] += int(res[0])
        classifica_reale[hid]["gs"] += int(res[1])
        classifica_reale[aid]["gf"] += int(res[1])
        classifica_reale[aid]["gs"] += int(res[0])
        classifica_reale[hid]["tot"] += m["ptH"]
        classifica_reale[aid]["tot"] += m["ptA"]
        
        # What-If
        b_h = best_scores.get((g, hid), m["ptH"])
        b_a = best_scores.get((g, aid), m["ptA"])
        gh = calcola_gol(b_h)
        ga = calcola_gol(b_a)
        
        if gh > ga:
            sp_h, sp_a = 3, 0
        elif gh < ga:
            sp_h, sp_a = 0, 3
        else:
            sp_h, sp_a = 1, 1
            
        classifica_whatif[hid]["punti"] += sp_h
        classifica_whatif[aid]["punti"] += sp_a
        classifica_whatif[hid]["gf"] += gh
        classifica_whatif[hid]["gs"] += ga
        classifica_whatif[aid]["gf"] += ga
        classifica_whatif[aid]["gs"] += gh
        classifica_whatif[hid]["tot"] += b_h
        classifica_whatif[aid]["tot"] += b_a

print("\n=== CONFRONTO CLASSIFICA REALE vs WHAT-IF ===")
for tid in sorted(classifica_reale.keys(), key=lambda x: classifica_whatif[x]["punti"], reverse=True):
    r = classifica_reale[tid]
    w = classifica_whatif[tid]
    diff = w["punti"] - r["punti"]
    diff_str = f"+{diff}" if diff > 0 else str(diff)
    print(f"{r['nome']:<16} | Reale: {r['punti']} pt (Tot {r['tot']:.1f}) | What-If: {w['punti']} pt (Tot {w['tot']:.1f}) | Diff: {diff_str} pt")

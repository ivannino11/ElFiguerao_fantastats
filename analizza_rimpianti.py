import json
import sys
import pandas as pd

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 1. Carica dati
with open("giocatori_rose.json", "r", encoding="utf-8") as f:
    players_data = json.load(f)["players"]
    players = {p["id"]: p for p in players_data}

with open("squadre_fanta.json", "r", encoding="utf-8") as f:
    teams_data = json.load(f)["data"]
    teams_map = {t["id"]: t["n"] for t in teams_data}

RUOLI = {1: "P", 2: "D", 3: "C", 4: "A"}

def analizza_giornata(file_lineup, num_giornata):
    with open(file_lineup, "r", encoding="utf-8") as f:
        lineup = json.load(f)

    rimpianti_totali = []

    for t in lineup:
        tid = t["tid"]
        tname = teams_map.get(tid, f"Team {tid}")
        tot_squadra = t.get("tot", 0)
        modulo = t.get("mdl", "")
        nmodulo = t.get("nmdl", "")

        # Gestione sostituzioni da stringa swtc
        # Formato swtc: pid_out;pid_in;...
        sub_in = set()
        swtc_str = t.get("swtc") or ""
        if swtc_str:
            parts = swtc_str.split(";")
            # Ogni sostituzione ha blocchi di parametri
            # es: 4364;5119;1;343;6 dove 5119 è entrato
            if len(parts) >= 2:
                try:
                    sub_in.add(int(parts[1]))
                except ValueError:
                    pass

        # Analisi panchinari
        for p in t.get("bench", []):
            pid = p.get("pid")
            if pid in sub_in:
                continue  # è entrato in campo, non è un rimpianto da panchina!

            scr = p.get("scr")
            cscr = p.get("cscr")

            # In Fantacalcio scr = 56 significa "senza voto" (s.v.)
            if scr == 56 or cscr is None or cscr >= 50:
                continue

            b = (p.get("b") or "").split(";")
            gol = int(b[2]) if len(b) > 2 and b[2] else 0
            rig_gol = int(b[6]) if len(b) > 6 and b[6] else 0
            tot_gol = gol + rig_gol
            assist = (int(b[12]) if len(b) > 12 and b[12] else 0) + (int(b[13]) if len(b) > 13 and b[13] else 0)
            clean_sheet = int(b[10]) if len(b) > 10 and b[10] else 0

            # È un rimpianto se ha fatto gol, assist, o fantavoto >= 7.0
            if tot_gol > 0 or assist > 0 or cscr >= 7.0:
                pinfo = players.get(pid, {})
                ruolo_num = pinfo.get("fcrle", 0)
                rimpianti_totali.append({
                    "giornata": num_giornata,
                    "squadra": tname,
                    "modulo": modulo,
                    "giocatore": pinfo.get("name", f"ID {pid}"),
                    "ruolo": RUOLI.get(ruolo_num, "?"),
                    "voto_puro": scr,
                    "fantavoto": cscr,
                    "gol": tot_gol,
                    "assist": assist,
                    "clean_sheet": clean_sheet,
                })

    df = pd.DataFrame(rimpianti_totali)
    return df

if __name__ == "__main__":
    tutti_rimpianti = []
    
    for g, fname in [(1, "lineup_giornata_1.json"), (2, "lineup_giornata_2.json")]:
        print(f"\n=======================================================")
        print(f"📊 REPORT RIMPIANTI DA PANCHINA - GIORNATA {g}")
        print(f"=======================================================")
        df_g = analizza_giornata(fname, g)
        if not df_g.empty:
            tutti_rimpianti.append(df_g)
            df_sorted = df_g.sort_values(by=["fantavoto", "gol"], ascending=False)
            for _, r in df_sorted.iterrows():
                motivo = []
                if r['gol'] > 0:
                    motivo.append(f"{r['gol']} GOL ⚽")
                if r['assist'] > 0:
                    motivo.append(f"{r['assist']} ASSIST 👟")
                if r['fantavoto'] >= 7.0 and not motivo:
                    motivo.append(f"Voto alto ⭐")
                motivo_str = ", ".join(motivo)
                print(f"[{r['squadra']}] {r['giocatore']} ({r['ruolo']}) -> Fantavoto: {r['fantavoto']} (Voto: {r['voto_puro']}) | {motivo_str}")
        else:
            print("Nessun rimpianto registrato.")

    if tutti_rimpianti:
        df_all = pd.concat(tutti_rimpianti, ignore_index=True)
        
        print("\n" + "=" * 60)
        print("🏆 CLASSIFICA GENERALE BONUS LASCIATI IN PANCHINA")
        print("=" * 60)
        
        # Aggreghiamo per squadra
        classifica = df_all.groupby("squadra").agg(
            gol_in_panchina=("gol", "sum"),
            assist_in_panchina=("assist", "sum"),
            totale_rimpianti=("giocatore", "count"),
            fantamedia_rimpianti=("fantavoto", "mean")
        ).reset_index()
        
        classifica["fantamedia_rimpianti"] = classifica["fantamedia_rimpianti"].round(2)
        classifica = classifica.sort_values(by=["gol_in_panchina", "assist_in_panchina"], ascending=False)
        
        for idx, row in classifica.iterrows():
            print(f"• {row['squadra']}: {row['gol_in_panchina']} Gol ⚽, {row['assist_in_panchina']} Assist 👟 lasciati in panchina ({row['totale_rimpianti']} giocatori con fv >= 7)")

import json
import re
import sys
import time
from curl_cffi import requests

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Estrai token autenticato
with open("fanta_dev_1.py", "r", encoding="utf-8") as f:
    m = re.search(r'"authorization":\s*"Bearer ([^"]+)"', f.read())
    TOKEN = m.group(1).strip()

COMPETITION_ID = "619614"
LEAGUE_ID = "3595294"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "app_key": "ICiELOObd5DF5uJEATi77CRvHiiRuMU0",
    "authorization": f"Bearer {TOKEN}",
    "origin": "https://leghe.fantacalcio.it",
    "referer": "https://leghe.fantacalcio.it/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

def fetch_json(url, desc=""):
    for imp in ["chrome124", "chrome119"]:
        for attempt in range(3):
            try:
                r = requests.get(url, headers=HEADERS, impersonate=imp, timeout=10)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 401:
                    print(f"Errore 401 (Token scaduto o non valido) su {desc}")
                    return None
            except Exception as e:
                time.sleep(1)
    print(f"Impossibile scaricare: {desc}")
    return None

def scarica_tutto():
    print(">>> 1. Scarico Elenco Squadre...")
    squadre = fetch_json(
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams?competitionId={COMPETITION_ID}&page=1&pageSize=50",
        "Squadre"
    )
    if squadre:
        with open("squadre_fanta.json", "w", encoding="utf-8") as f:
            json.dump(squadre, f, indent=2, ensure_ascii=False)
        print("    [OK] Salvato squadre_fanta.json")

    time.sleep(1)

    print(">>> 2. Scarico Anagrafica e Statistiche Calciatori...")
    players = fetch_json(
        f"https://apileague.fantacalcio.it/onboarding/v1/league/players?leagueId={LEAGUE_ID}",
        "Calciatori"
    )
    if players:
        with open("giocatori_rose.json", "w", encoding="utf-8") as f:
            json.dump(players, f, indent=2, ensure_ascii=False)
        print("    [OK] Salvato giocatori_rose.json")

    time.sleep(1)

    print(">>> 3. Scarico Calendario Completo...")
    calendario = fetch_json(
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/calendar/{COMPETITION_ID}",
        "Calendario"
    )
    if calendario:
        with open("calendario.json", "w", encoding="utf-8") as f:
            json.dump(calendario, f, indent=2, ensure_ascii=False)
        print("    [OK] Salvato calendario.json")

        # Scarica le formazioni di tutte le giornate già calcolate!
        print(">>> 4. Scarico Formazioni e Voti delle giornate calcolate...")
        for turno in calendario:
            if turno.get("calculated", False):
                g_lega = turno.get("matchDay")
                g_serie_a = turno.get("championshipMatchDay")
                url_lineup = f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{COMPETITION_ID}/{g_lega}/{g_serie_a}"
                time.sleep(1)
                data_lineup = fetch_json(url_lineup, f"Formazioni Giornata {g_lega} (Serie A {g_serie_a})")
                if data_lineup:
                    filename = f"lineup_giornata_{g_lega}.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data_lineup, f, indent=2, ensure_ascii=False)
                    print(f"    [OK] Salvato {filename}")

    print("\nDownload completato con successo!")

if __name__ == "__main__":
    scarica_tutto()

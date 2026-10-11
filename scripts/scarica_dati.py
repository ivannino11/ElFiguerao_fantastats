import json
import sys
import time
from curl_cffi import requests

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fanta_utils import headers_api, percorso_dati, DATA_DIR
import os

COMPETITION_ID = "619614"
LEAGUE_ID = "3595294"

HEADERS = headers_api()  # token letto da .env / FANTA_TOKEN

ERRORI = []  # download falliti: se non vuota lo script esce con codice 1

def fetch_json(url, desc=""):
    ultimo = "nessuna risposta"
    for imp in ["chrome124", "chrome119"]:
        for attempt in range(3):
            try:
                r = requests.get(url, headers=HEADERS, impersonate=imp, timeout=10)
                ultimo = f"HTTP {r.status_code}"
                if r.status_code in (403, 503) and ("cf-ray" in r.headers or "cloudflare" in r.text[:2000].lower()):
                    ultimo = f"HTTP {r.status_code} bloccato da Cloudflare"
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 401:
                    print(f"Errore 401 (Token scaduto o non valido) su {desc}")
                    ERRORI.append(f"{desc}: 401 token scaduto o non valido")
                    return None
            except Exception as e:
                ultimo = f"errore di rete ({type(e).__name__})"
                time.sleep(1)
    print(f"Impossibile scaricare: {desc} [{ultimo}]")
    ERRORI.append(f"{desc}: download non riuscito ({ultimo})")
    return None

def scarica_tutto():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(">>> 1. Scarico Elenco Squadre...")
    squadre = fetch_json(
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams?competitionId={COMPETITION_ID}&page=1&pageSize=50",
        "Squadre"
    )
    if squadre:
        with open(percorso_dati("squadre_fanta.json"), "w", encoding="utf-8") as f:
            json.dump(squadre, f, indent=2, ensure_ascii=False)
        print("    [OK] Salvato squadre_fanta.json")

    time.sleep(1)

    print(">>> 2. Scarico Anagrafica e Statistiche Calciatori...")
    players = fetch_json(
        f"https://apileague.fantacalcio.it/onboarding/v1/league/players?leagueId={LEAGUE_ID}",
        "Calciatori"
    )
    if players:
        with open(percorso_dati("giocatori_rose.json"), "w", encoding="utf-8") as f:
            json.dump(players, f, indent=2, ensure_ascii=False)
        print("    [OK] Salvato giocatori_rose.json")

    time.sleep(1)

    print(">>> 3. Scarico Calendario Completo...")
    calendario = fetch_json(
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/calendar/{COMPETITION_ID}",
        "Calendario"
    )
    if calendario:
        with open(percorso_dati("calendario.json"), "w", encoding="utf-8") as f:
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
                    with open(percorso_dati(filename), "w", encoding="utf-8") as f:
                        json.dump(data_lineup, f, indent=2, ensure_ascii=False)
                    print(f"    [OK] Salvato {filename}")

    if ERRORI:
        print("\nDownload NON completato, errori:")
        for e in ERRORI:
            print(f"  - {e}")
        return False
    print("\nDownload completato con successo!")
    return True

if __name__ == "__main__":
    sys.exit(0 if scarica_tutto() else 1)

import requests
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from fanta_utils import headers_api

COMPETITION_ID = "619614"

HEADERS = headers_api()  # token letto da .env / FANTA_TOKEN

# Proviamo varianti reali basate sul prefisso /onboarding/v1/league/...
endpoints_da_testare = [
    (
        "Squadre",
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams?page=1&pageSize=50&competitionId={COMPETITION_ID}",
    ),
    (
        "Classifica / Standings",
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/standings?competitionId={COMPETITION_ID}",
    ),
    (
        "Giornate / Calendario",
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/rounds?competitionId={COMPETITION_ID}",
    ),
    (
        "Rose / Roster",
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/squads?competitionId={COMPETITION_ID}",
    ),
    (
        "Statistiche",
        f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/statistics?competitionId={COMPETITION_ID}",
    ),
]

print("Riprovo la scansione con i parametri corretti...\n")

for nome, url in endpoints_da_testare:
  try:
    response = requests.get(url, headers=HEADERS, timeout=5)
    if response.status_code == 200:
      print(f"[TROVATO! 200 OK] {nome} -> {url}")
    else:
      print(f"[{response.status_code}] {nome}")
  except Exception as e:
    print(f"[ERRORE] {nome}")
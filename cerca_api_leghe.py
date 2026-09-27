import requests

COMPETITION_ID = "619614"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "app_key": "ICiELOObd5DF5uJEATi77CRvHiiRuMU0",
    "authorization": "Bearer ***RIMOSSO***",
    "origin": "https://leghe.fantacalcio.it",
    "referer": "https://leghe.fantacalcio.it/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
}

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
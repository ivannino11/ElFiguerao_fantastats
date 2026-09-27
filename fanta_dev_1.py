import json
from curl_cffi import requests

URL = "https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams"
COMPETITION_ID = "619614"

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "app_key": "ICiELOObd5DF5uJEATi77CRvHiiRuMU0",
    "authorization": "Bearer ***RIMOSSO***",
    "origin": "https://leghe.fantacalcio.it",
    "referer": "https://leghe.fantacalcio.it/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

PARAMS = {"page": 1, "pageSize": 50, "competitionId": COMPETITION_ID}

try:
  print("Invio richiesta con fingerprinting browser simulato...")
  # impersonate='chrome120' o 'chrome110' simula perfettamente la mano di un browser Chrome
  response = requests.get(
      URL, params=PARAMS, headers=headers, impersonate="chrome120", timeout=10
  )
  print(f"Status Code ricevuto: {response.status_code}")

  if response.status_code == 200:
    data = response.json()
    output_path = r"C:\Users\ivann\Analisi dati\squadre_fanta.json"

    with open(output_path, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"SUCCESSO! File salvato in: {output_path}")
  else:
    print(f"Errore dal server: {response.status_code} - {response.text}")

except Exception as e:
  print(f"Errore durante la richiesta: {e}")
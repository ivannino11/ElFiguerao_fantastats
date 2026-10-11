import json
from curl_cffi import requests
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from fanta_utils import headers_api, percorso_dati

URL = "https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams"
COMPETITION_ID = "619614"

headers = headers_api()  # token letto da .env / FANTA_TOKEN

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
    output_path = percorso_dati("squadre_fanta.json")

    with open(output_path, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"SUCCESSO! File salvato in: {output_path}")
  else:
    print(f"Errore dal server: {response.status_code} - {response.text}")

except Exception as e:
  print(f"Errore durante la richiesta: {e}")
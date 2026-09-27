
import pandas as pd
import requests

# Configurazione
BASE_URL = "https://apileague.fantacalcio.it"
COMPETITION_ID = "619614"

# Inserisci qui il token o i cookie che trovi negli headers della richiesta dal browser
HEADERS = {
    "Authorization": "Bearer ***RIMOSSO***",  # Oppure i cookie se richiesto
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def get_teams():
  url = f"{BASE_URL}/onboarding/v1/league/competition/teams"
  params = {"page": 1, "pageSize": 50, "competitionId": COMPETITION_ID}

  response = requests.get(url, headers=HEADERS, params=params)

  if response.status_code == 200:
    data = response.json()
    return data
  else:
    print(f"Errore {response.status_code}: {response.text}")
    return None


# Esempio di utilizzo
if __name__ == "__main__":
  teams_data = get_teams()
  if teams_data:
    print("Squadre scaricate con successo!")
    # Qui potrai esplorare la struttura del JSON (es. con Pandas)

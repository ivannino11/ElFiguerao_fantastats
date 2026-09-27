
import pandas as pd
import requests

# Configurazione
BASE_URL = "https://apileague.fantacalcio.it"
COMPETITION_ID = "619614"

# Inserisci qui il token o i cookie che trovi negli headers della richiesta dal browser
HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Im9OUVhqWXhvQ3ZscFVnVDdCQkdYTHhwUGxxT0k1c0lqWVdyQXhhWFpTczAiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiI5MTFjNzg5MGIwYzllZTJkNmUwODIwMzcyMzhiODU3MCIsImp0aSI6IjgwN2Y3NGUzMWQ3MDJlODU3ZjczNTg5NGEwNTRjZjI0IiwiaXNzIjoiaHR0cHM6Ly9sZWdoZS5mYW50YWNhbGNpby5pdCIsImlhdCI6MTc5MDIwMDA4MSwiZXhwIjoxODIxNzM2MDgxLCJsX2lkIjoiMzU5NTI5NCIsInRfaWQiOiIxNjc2NTAyMSIsInVzZXJfaWQiOiIyODQxNjkzIiwic3RfbGVhZ3VlcyI6IjE3OTAyMDAwODE4NDMiLCJzdF9hdXRoIjoiMTY4MzEwOTA3OTk0MiIsInJvbGUiOiJ1c2VyX2xlYWd1ZSIsInRva2VuX3VzZSI6ImlkIiwibmJmIjoxNzkwMjAwMDgxLCJhdWQiOiJmYW50YWNhbGNpbyJ9.QZXO0lgq-JbAc65pfhlmnge7B9xuNo1zuPm1zkl9nO6NAuLDH3Lq2lu4QjWaFQnPc_IyUYxSheBoXqfE5PUjrEnBmeQ28UDw9NFAB1dqyu_l_qk9mqTvXBcpPsdSj4KVg0pElN7_FEbTJ4h7HnjykohdHIMv1KMjFDYtpZmuH5QgGKjGR8oGInbY68yP90CADKvcFR9qrrC5dlQcYZC2AicT9c6urBBMpn5IQ7vWQdv6OwDTq6fKuogVoo9q6HngB3MfPwRcQ_0HWZGrY9CxvXyyj44nh4bfc8UYLS2UG38CL4dQWcKPnKL2-GV8HIiNlKPAURw8ow5KkCvcwJxbjg",  # Oppure i cookie se richiesto
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

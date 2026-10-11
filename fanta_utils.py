"""Funzioni condivise per leggere le formazioni (lineup_giornata_X.json).

Gestione delle sostituzioni
---------------------------
Le sostituzioni realmente avvenute sono indicate dal campo ``ptype`` di ogni giocatore:
  - ``"U"`` sul titolare uscito (senza voto, sostituito)
  - ``"E"`` sul panchinaro entrato in campo
Il punteggio ufficiale della squadra torna sempre come:
  tot = somma(cscr titolari non "U") + somma(cscr panchinari "E") + somma(tbon)

Il campo ``swtc`` NON è l'elenco dei cambi avvenuti: è la regola di sostituzione
tattica impostata dall'allenatore (formato ``out;in;condizione;modulo;soglia``,
``0;0;0;0;0`` se non impostata) e non va usato per capire chi è entrato.
"""

USCITO = "U"
ENTRATO = "E"
SENZA_VOTO = (55, 56)  # scr 55/56 = senza voto (s.v.)


def ha_voto(p):
    """True se il giocatore ha un fantavoto valido."""
    cscr = p.get("cscr")
    return (
        p.get("scr") not in SENZA_VOTO
        and isinstance(cscr, (int, float))
        and cscr < 50
    )


def giocatori_entrati(team_lineup):
    """Insieme dei pid dei panchinari entrati in campo (tutte le sostituzioni)."""
    return {p["pid"] for p in team_lineup.get("bench", []) if p.get("ptype") == ENTRATO}


def giocatori_usciti(team_lineup):
    """Insieme dei pid dei titolari sostituiti."""
    return {p["pid"] for p in team_lineup.get("starts", []) if p.get("ptype") == USCITO}


def formazione_effettiva(team_lineup):
    """Gli undici che hanno realmente preso punti: titolari non usciti + panchinari entrati."""
    titolari = [p for p in team_lineup.get("starts", []) if p.get("ptype") != USCITO]
    entrati = [p for p in team_lineup.get("bench", []) if p.get("ptype") == ENTRATO]
    return titolari + entrati


def panchina_effettiva(team_lineup):
    """I panchinari rimasti fuori (non entrati)."""
    return [p for p in team_lineup.get("bench", []) if p.get("ptype") != ENTRATO]


def bonus_squadra(team_lineup):
    """Somma dei bonus di squadra (campo tbon, es. modificatori)."""
    tot = 0.0
    for x in (team_lineup.get("tbon") or "").split(";"):
        try:
            tot += float(x)
        except ValueError:
            pass
    return tot


def giornate_disponibili(cartella="."):
    """Elenco ordinato di (giornata_lega, percorso_file) per ogni lineup_giornata_X.json presente."""
    import glob
    import os
    import re

    giornate = []
    for path in glob.glob(os.path.join(cartella, "lineup_giornata_*.json")):
        m = re.search(r"lineup_giornata_(\d+)\.json$", os.path.basename(path))
        if m:
            giornate.append((int(m.group(1)), path))
    return sorted(giornate)


# ------------------------------------------------------------
# Credenziali API (token Bearer)
# ------------------------------------------------------------
# Il token NON va mai scritto nel codice: si legge dalla variabile d'ambiente
# FANTA_TOKEN oppure dal file .env nella cartella del progetto (escluso da git).
# Formato del file .env:   FANTA_TOKEN=eyJhbGciOi...

APP_KEY = "ICiELOObd5DF5uJEATi77CRvHiiRuMU0"  # chiave pubblica del frontend web, uguale per tutti


def _leggi_env_file(path):
    valori = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for riga in f:
                riga = riga.strip()
                if not riga or riga.startswith("#") or "=" not in riga:
                    continue
                k, v = riga.split("=", 1)
                valori[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return valori


def _scadenza_jwt(token):
    """Data di scadenza (UTC) del JWT, senza verificarne la firma. None se non leggibile."""
    import base64
    import json
    from datetime import datetime, timezone

    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except Exception:
        return None


def carica_token():
    """Restituisce il token Bearer da FANTA_TOKEN o da .env; esce con errore chiaro se manca o è scaduto."""
    import os
    import sys
    from datetime import datetime, timezone

    cartella = os.path.dirname(os.path.abspath(__file__))
    token = os.environ.get("FANTA_TOKEN") or _leggi_env_file(os.path.join(cartella, ".env")).get("FANTA_TOKEN", "")
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        sys.exit(
            "[ERRORE] Token mancante. Crea il file .env nella cartella del progetto con la riga:\n"
            "         FANTA_TOKEN=<il tuo token Bearer di leghe.fantacalcio.it>\n"
            "         (vedi .env.example)"
        )

    scad = _scadenza_jwt(token)
    if scad and scad <= datetime.now(timezone.utc):
        sys.exit(f"[ERRORE] Il token è scaduto il {scad:%d/%m/%Y}: prendine uno nuovo e aggiorna .env")
    return token


def headers_api(token=None):
    """Header HTTP per le API apileague.fantacalcio.it."""
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "app_key": APP_KEY,
        "authorization": f"Bearer {token or carica_token()}",
        "origin": "https://leghe.fantacalcio.it",
        "referer": "https://leghe.fantacalcio.it/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

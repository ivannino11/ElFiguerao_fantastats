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

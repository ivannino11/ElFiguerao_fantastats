PROGETTO: Analisi Avanzata Fantacalcio (API Leghe Fantacalcio)
🎯 Obiettivo del Progetto
Sviluppare un sistema di script Python locali per estrarre, elaborare e analizzare dati avanzati e statistiche non mostrate dall'applicazione ufficiale di leghe.fantacalcio.it (Competizione ID: 619614).

🛠️ Stack Tecnologico e Ambiente
Linguaggio: Python 3.12

Ambiente di sviluppo: VS Code / Antigravity CLI (agy)

Librerie chiave: curl_cffi (per aggirare Cloudflare con impersonificazione browser chrome120), requests, pandas, beautifulsoup4.

Percorso dati locali: C:\Users\ivann\Analisi dati

🔑 Mappa delle API e dei File JSON mappati e scaricati
I dati grezzi vengono estratti tramite curl_cffi (impersonate='chrome124' per aggirare Cloudflare) e salvati in locale:

- squadre_fanta.json: https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams?competitionId=619614&page=1&pageSize=50
  -> Elenco 10 squadre, crediti, ID calciatori e prezzi d'acquisto.

- giocatori_rose.json: https://apileague.fantacalcio.it/onboarding/v1/league/players?leagueId=3595294
  -> Anagrafica completa dei 598 calciatori Serie A (ID, Nome, Ruolo Classic, Squadra Serie A, Quotazioni, Medie voto, Fantamedie).

- calendario.json: https://apileague.fantacalcio.it/onboarding/v1/league/competition/calendar/619614
  -> Calendario completo 35 turni, giornate calcolate, accoppiamenti e risultati.

- lineup_giornata_{X}.json: https://apileague.fantacalcio.it/gaming/v1/teamLineup/619614/{giornata_lega}/{giornata_serie_a}
  -> Formazioni turno per turno (starts=titolari, bench=panchina, swtc=sostituzioni, mdl/nmdl=moduli tattici, voti, cscr=fantavoti e bonus vettoriali 'b').

- status.json: https://apileague.fantacalcio.it/onboarding/v1/league/status?leagueId=3595294
  -> Stato lega, giornata attiva.

📊 Script Sviluppati e Funzionali
1. scarica_dati.py: Motore unificato di download con curl_cffi per scaricare squadre, giocatori, calendario e automaticamente tutti i lineup delle giornate calcolate.
2. analizza_rimpianti.py: Motore analitico che incrocia formazioni, panchine, sostituzioni e anagrafica per estrarre:
   - Rimpianti turno per turno (chi ha segnato o preso voto >= 7.0 in panchina senza subentrare).
   - Classifica generale dei gol e assist lasciati in panchina per squadra.

🚀 Prossimi Passi
1. Costruire DataFrame Pandas strutturati ed esportabili (es. Excel/CSV o report).
2. Implementare analisi dei Top Player per squadra (chi ha più gol/assist/FM).
3. Analisi comparativa dei moduli tattici (es. 3-4-3 vs 3-5-2) per rendimento medio punti.
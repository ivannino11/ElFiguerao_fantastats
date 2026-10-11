# ElFiguerao_fantastats

Statistiche alternative della lega privata di fantacalcio **El Figuerao** (leghe.fantacalcio.it), quelle che il sito ufficiale non mostra: rimpianti dalla panchina, classifica "What-If" con la formazione ottimale, top player per squadra, rendimento dei moduli, rose e budget.

**Dashboard pubblica:** https://ivannino11.github.io/ElFiguerao_fantastats/

> Il lavoro si fa sul branch **`test`**: è quello pubblicato da GitHub Pages.

---

## Indice
1. [Come funziona](#come-funziona)
2. [Installazione](#installazione)
3. [Il token (credenziali)](#il-token-credenziali)
4. [Aggiornare la dashboard](#aggiornare-la-dashboard)
5. [Come contribuire](#come-contribuire)
6. [Problemi comuni](#problemi-comuni)

---

## Come funziona

```
leghe.fantacalcio.it (API)  →  scarica_dati.py  →  file *.json  →  genera_dashboard.py  →  index.html  →  GitHub Pages
```

| File | A cosa serve |
|---|---|
| `aggiorna.bat` | Fa tutto con un clic: scarica i dati, rigenera la pagina e la pubblica |
| `scarica_dati.py` | Scarica squadre, calciatori, calendario e formazioni delle giornate calcolate |
| `genera_dashboard.py` | Genera `index.html` (la pagina pubblica) con i dati incorporati |
| `analizza_rimpianti.py` | Report a terminale dei bonus lasciati in panchina |
| `test_whatif.py` | Report a terminale della classifica What-If |
| `fanta_utils.py` | Funzioni condivise: sostituzioni, giornate disponibili, token e header API |
| `*.json` | Dati grezzi scaricati dalle API (vengono riscaricati a ogni aggiornamento) |
| `index.html` | **Generato automaticamente: non modificarlo a mano** |
| `CONTEXT_FCSTATS.md` | Note tecniche: API, formato dei dati, regole di calcolo |

---

## Installazione

Serve una volta sola.

**Requisiti**
- [Git](https://git-scm.com/download/win)
- [Python 3.12+](https://www.python.org/downloads/) (durante l'installazione spunta "Add Python to PATH")
- Essere iscritti alla lega El Figuerao su leghe.fantacalcio.it

**Comandi** (dal terminale, nella cartella dove vuoi il progetto):
```
git clone -b test https://github.com/ivannino11/ElFiguerao_fantastats.git
cd ElFiguerao_fantastats
pip install -r requirements.txt
```

---

## Il token (credenziali)

Gli script usano il **tuo** token personale di leghe.fantacalcio.it. Ognuno usa il proprio; non serve quello del proprietario del repo.

> ⚠️ Il token è come una password: **non scriverlo mai nel codice, non metterlo in un commit e non mandarlo in chat.**
> Il file `.env` è già escluso da git (`.gitignore`), quindi lì è al sicuro.

### Come prendere il token
1. Apri https://leghe.fantacalcio.it ed entra nella lega El Figuerao
2. Premi **F12** e vai sulla scheda **Rete** (Network)
3. Ricarica la pagina (**F5**) e scrivi `apileague` nel filtro
4. Clicca una richiesta e, in **Intestazioni richiesta** (Request Headers), copia il valore di **`authorization`**: inizia con `Bearer eyJ...`

### Dove metterlo: scegli uno dei tre modi

**Modo 1: automatico (il più semplice)**
Lancia `aggiorna.bat` o `python scarica_dati.py`. Se il token manca, lo script te lo chiede: incollalo (va bene anche con `Bearer ` davanti) e premi Invio. Viene salvato da solo nel file `.env` e non te lo chiederà più.

**Modo 2: file `.env` a mano**
```
copy .env.example .env
notepad .env
```
Sostituisci `incolla_qui_il_token` con il token, senza virgolette e senza andare a capo:
```
FANTA_TOKEN=eyJhbGciOiJSUzI1NiIs...
```
Non creare il file con "Salva con nome" del Blocco note: spesso diventa `.env.txt` e non viene trovato.

**Modo 3: variabile d'ambiente di Windows** (utile se lavori da più cartelle)
```
setx FANTA_TOKEN "eyJhbGciOiJSUzI1NiIs..."
```
Chiudi e riapri il terminale. Se la variabile è presente ha la precedenza su `.env`.

### Verifica
```
python -c "from fanta_utils import carica_token, _scadenza_jwt; print('OK, scade il', _scadenza_jwt(carica_token()).date())"
```
Quando il token scade, gli script si fermano con un messaggio chiaro: prendine uno nuovo e sostituiscilo (con il Modo 1 basta cancellare `.env` e rilanciare).

---

## Aggiornare la dashboard

### Windows: `aggiorna.bat`
Non servono comandi né parametri. Puoi:
- fare **doppio clic** su `aggiorna.bat` dalla cartella del progetto, oppure
- lanciarlo dal terminale: `aggiorna.bat` dal Prompt dei comandi, `.\aggiorna.bat` da PowerShell

Lo script:
1. allinea la cartella con GitHub (`git pull`)
2. scarica i dati nuovi (`scarica_dati.py`); se qualcosa va storto si ferma senza pubblicare nulla
3. rigenera `index.html` (`genera_dashboard.py`)
4. fa commit e push sul branch `test`; dopo 1-2 minuti la pagina pubblica è aggiornata

Se non ci sono novità te lo dice e non pubblica niente. Per pubblicare serve il permesso di scrittura sul repo (vedi sotto).

Se vuoi solo vedere il risultato senza pubblicarlo:
```
python scarica_dati.py
python genera_dashboard.py
```
e apri `index.html` con doppio clic.

### Mac / Linux
```
git pull --rebase --autostash origin test
python3 scarica_dati.py && python3 genera_dashboard.py
git add index.html *.json
git commit -m "Aggiornamento dati"
git push origin test
```

---

## Come contribuire

### Permessi
- **Collaboratore** (consigliato per chi è nella lega): il proprietario ti aggiunge da *Settings → Collaborators*. Puoi pubblicare con `aggiorna.bat` e creare branch.
- **Senza permessi**: fai un *Fork*, lavora sulla tua copia e apri una *Pull Request* verso il branch `test`.

### Flusso di lavoro per modificare il codice
```
git checkout test
git pull origin test
git checkout -b nome-modifica            # es. fix-classifica-moduli
# ... modifica, prova in locale ...
git add <file modificati>
git commit -m "Descrizione chiara della modifica"
git push origin nome-modifica
```
Poi apri una Pull Request da `nome-modifica` verso `test` su GitHub. Il semplice aggiornamento dei dati con `aggiorna.bat` invece va direttamente su `test`.

### Regole
- **Non modificare `index.html` a mano**: viene rigenerato a ogni aggiornamento. Grafica e contenuti della pagina si cambiano in `genera_dashboard.py`.
- **Niente token nel codice**: usa sempre `headers_api()` di `fanta_utils.py` per chiamare le API.
- **Logica condivisa in `fanta_utils.py`**: per esempio, chi è entrato o uscito si legge con `giocatori_entrati()`, `formazione_effettiva()` e `panchina_effettiva()`, mai dal campo `swtc`.
- **Prova prima di pubblicare**: lancia `python genera_dashboard.py` e controlla `index.html`, anche da mobile (F12 → icona telefono).
- **Prima di toccare i calcoli** leggi `CONTEXT_FCSTATS.md` (formato dei dati, sostituzioni, bonus).

---

## Problemi comuni

| Messaggio | Soluzione |
|---|---|
| `Token mancante` | Vedi [Il token](#il-token-credenziali) |
| `Il token è scaduto` / errore `401` | Prendi un token nuovo e sostituiscilo in `.env` |
| `Your local changes ... would be overwritten by merge` | `git checkout -- index.html` (o il file indicato), poi riprova |
| `Sei sul branch "main"` | `git checkout test` |
| `git push` rifiutato / permesso negato | Non sei collaboratore: chiedi l'accesso o usa Fork + Pull Request |
| `python` non riconosciuto | Reinstalla Python spuntando "Add Python to PATH", oppure usa `py` al posto di `python` |
| La pagina pubblica non cambia | Aspetta 1-2 minuti e ricarica con **Ctrl+F5** |

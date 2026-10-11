# ElFiguerao_fantastats

Statistiche alternative della lega privata di fantacalcio **El Figuerao** (leghe.fantacalcio.it), quelle che il sito ufficiale non mostra: rimpianti dalla panchina, classifica "What-If" con la formazione ottimale, top player per squadra, rendimento dei moduli, rose e budget.

**Dashboard pubblica:** https://ivannino11.github.io/ElFiguerao_fantastats/

> Il branch principale è **`main`**: è quello pubblicato da GitHub Pages (cartella `docs/`). Le modifiche al codice passano da branch temporanei e Pull Request.

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
leghe.fantacalcio.it (API) → scripts/scarica_dati.py → data/*.json → scripts/genera_dashboard.py → docs/index.html → GitHub Pages
```

### Struttura delle cartelle

```
ElFiguerao_fantastats/
├── aggiorna.bat              ← aggiorna e pubblica con un doppio clic (Windows)
├── README.md                 ← questa guida
├── CONTEXT_FCSTATS.md        ← note tecniche: API, formato dei dati, regole di calcolo
├── requirements.txt          ← librerie Python
├── .env.example              ← modello per il file .env con il token
├── .github/workflows/
│   └── aggiorna.yml          ← aggiornamento da GitHub / smartphone (GitHub Actions)
├── scripts/                  ← il codice
│   ├── fanta_utils.py        ← funzioni condivise: percorsi, sostituzioni, giornate, token
│   ├── scarica_dati.py       ← scarica i dati dalle API in data/
│   ├── genera_dashboard.py   ← genera docs/index.html
│   ├── analizza_rimpianti.py ← report a terminale dei bonus lasciati in panchina
│   └── test_whatif.py        ← report a terminale della classifica What-If
├── data/                     ← JSON scaricati dalle API (riscaricati a ogni aggiornamento)
├── docs/
│   └── index.html            ← la pagina pubblica: GENERATA, non modificarla a mano
└── dev/                      ← script di esplorazione delle API (non servono per l'uso normale)
```

Gli script trovano da soli le cartelle `data/` e `docs/`: puoi lanciarli da qualunque cartella.

---

## Installazione

Serve una volta sola (non serve se aggiorni solo da smartphone, vedi [GitHub Actions](#da-smartphone-o-da-github-github-actions)).

**Requisiti**
- [Git](https://git-scm.com/download/win)
- [Python 3.12+](https://www.python.org/downloads/) (durante l'installazione spunta "Add Python to PATH")
- Essere iscritti alla lega El Figuerao su leghe.fantacalcio.it

**Comandi** (dal terminale, nella cartella dove vuoi il progetto):
```
git clone https://github.com/ivannino11/ElFiguerao_fantastats.git
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

### Dove metterlo sul PC: scegli uno dei tre modi

**Modo 1: automatico (il più semplice)**
Lancia `aggiorna.bat` o `python scripts/scarica_dati.py`. Se il token manca, lo script te lo chiede: incollalo (va bene anche con `Bearer ` davanti) e premi Invio. Viene salvato da solo nel file `.env` e non te lo chiederà più.

**Modo 2: file `.env` a mano**
Nella cartella principale del progetto:
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

### Per GitHub Actions (aggiornamento da smartphone)
Il token va salvato come **secret** del repo (solo il proprietario o chi ha accesso admin):
*Settings → Secrets and variables → Actions → New repository secret*, nome `FANTA_TOKEN`, valore il token (senza `Bearer `).
I secret sono cifrati: nessuno può leggerli, nemmeno nei log.

### Verifica
```
python -c "import sys; sys.path.insert(0, 'scripts'); from fanta_utils import carica_token, _scadenza_jwt; print('OK, scade il', _scadenza_jwt(carica_token()).date())"
```
Quando il token scade, gli script si fermano con un messaggio chiaro: prendine uno nuovo e sostituiscilo (con il Modo 1 basta cancellare `.env` e rilanciare; su GitHub aggiorna il secret).

---

## Aggiornare la dashboard

Tre modi, stesso risultato: scaricano i dati, rigenerano `docs/index.html` e lo pubblicano su `main`. Dopo 1-2 minuti la pagina pubblica è aggiornata. Se non ci sono novità non pubblicano niente. Se il download fallisce si fermano senza pubblicare.

### Da smartphone o da GitHub (GitHub Actions)
Non serve il PC acceso.
1. Apri l'app **GitHub Mobile** (o github.com dal browser) e vai sul repo
2. **Actions** → workflow **Aggiorna dashboard**
3. **Run workflow** → branch `main` → **Run workflow**
4. Dopo circa un minuto il pallino diventa verde. Se è rosso, apri l'esecuzione e leggi il messaggio del passo fallito

Serve il permesso di scrittura sul repo e il secret `FANTA_TOKEN` (vedi sopra). Dal PC si può lanciare anche con `gh workflow run aggiorna.yml`.

### Windows: `aggiorna.bat`
Non servono comandi né parametri. Puoi:
- fare **doppio clic** su `aggiorna.bat` dalla cartella del progetto, oppure
- lanciarlo dal terminale: `aggiorna.bat` dal Prompt dei comandi, `.\aggiorna.bat` da PowerShell

Lo script: allinea la cartella con GitHub (`git pull`), scarica i dati, rigenera la pagina, fa commit e push su `main`.

Se vuoi solo vedere il risultato senza pubblicarlo:
```
python scripts/scarica_dati.py
python scripts/genera_dashboard.py
```
e apri `docs/index.html` con doppio clic.

### Mac / Linux
```
git pull --rebase --autostash origin main
python3 scripts/scarica_dati.py && python3 scripts/genera_dashboard.py
git add docs/index.html data
git commit -m "Aggiornamento dati"
git push origin main
```

---

## Come contribuire

### Permessi
- **Collaboratore** (consigliato per chi è nella lega): il proprietario ti aggiunge da *Settings → Collaborators*. Puoi pubblicare (con `aggiorna.bat` o da GitHub Actions) e creare branch.
- **Senza permessi**: fai un *Fork*, lavora sulla tua copia e apri una *Pull Request* verso il branch `main`.

### Flusso di lavoro per modificare il codice
```
git checkout main
git pull origin main
git checkout -b nome-modifica            # es. fix-classifica-moduli
# ... modifica, prova in locale ...
git add <file modificati>
git commit -m "Descrizione chiara della modifica"
git push origin nome-modifica
```
Poi apri una Pull Request da `nome-modifica` verso `main` su GitHub. Il semplice aggiornamento dei dati invece va direttamente su `main`.

### Regole
- **Non modificare `docs/index.html` a mano**: viene rigenerato a ogni aggiornamento. Grafica e contenuti della pagina si cambiano in `scripts/genera_dashboard.py`.
- **Niente token nel codice**: usa sempre `headers_api()` di `scripts/fanta_utils.py` per chiamare le API.
- **Percorsi e logica condivisa in `scripts/fanta_utils.py`**: per i file dati usa `percorso_dati("nome.json")`; chi è entrato o uscito si legge con `giocatori_entrati()`, `formazione_effettiva()` e `panchina_effettiva()`, mai dal campo `swtc`.
- **Prova prima di pubblicare**: lancia `python scripts/genera_dashboard.py` e controlla `docs/index.html`, anche da mobile (F12 → icona telefono).
- **Prima di toccare i calcoli** leggi `CONTEXT_FCSTATS.md` (formato dei dati, sostituzioni, bonus).

---

## Problemi comuni

| Messaggio | Soluzione |
|---|---|
| `Token mancante` | Vedi [Il token](#il-token-credenziali) (su GitHub Actions: manca il secret `FANTA_TOKEN`) |
| `Il token è scaduto` / errore `401` | Prendi un token nuovo e sostituiscilo in `.env` o nel secret |
| `bloccato da Cloudflare` (GitHub Actions) | Il sito blocca i server di GitHub: aggiorna dal PC con `aggiorna.bat` |
| `Your local changes ... would be overwritten by merge` | `git checkout -- docs/index.html data`, poi riprova |
| `Sei sul branch "test"` (o un altro) | `git fetch origin`, `git checkout main`, `git reset --hard origin/main` |
| `git push` rifiutato / permesso negato | Non sei collaboratore: chiedi l'accesso o usa Fork + Pull Request |
| `python` non riconosciuto | Reinstalla Python spuntando "Add Python to PATH", oppure usa `py` al posto di `python` |
| La pagina pubblica non cambia | Aspetta 1-2 minuti e ricarica con **Ctrl+F5** |

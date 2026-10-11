@echo off
setlocal
chcp 65001 >nul
REM ============================================================
REM  aggiorna.bat - Aggiorna la dashboard pubblica El Figuerao
REM  1. allinea il repo  2. scarica i dati  3. rigenera docs\index.html
REM  4. commit + push sul branch main (GitHub Pages)
REM ============================================================
REM Lo script gira da una copia temporanea: cosi' git pull puo' aggiornare
REM aggiorna.bat senza disturbare l'esecuzione in corso.
if /i not "%~1"=="__copia" (
    copy /y "%~f0" "%TEMP%\aggiorna_elfiguerao.bat" >nul
    "%TEMP%\aggiorna_elfiguerao.bat" __copia "%~dp0."
)
cd /d "%~2"

set "PAGE_URL=https://ivannino11.github.io/ElFiguerao_fantastats/"

where python >nul 2>&1 && (set "PY=python") || (set "PY=py")

for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%b"
if /i not "%BRANCH%"=="main" (
    echo [ERRORE] Sei sul branch "%BRANCH%": GitHub Pages pubblica dal branch "main".
    echo          Esegui:  git fetch origin ^& git checkout main ^& git reset --hard origin/main
    goto :fail
)

echo.
echo === 1/4 Allineo il repo con GitHub ===
REM docs/index.html e i JSON in data/ vengono rigenerati/riscaricati a ogni giro:
REM scarto le copie locali per evitare conflitti con il pull.
git checkout -- docs/index.html data 2>nul
git pull --rebase --autostash origin main
if errorlevel 1 (
    echo [ERRORE] git pull non riuscito: risolvi i conflitti e riprova.
    goto :fail
)

echo.
echo === 2/4 Scarico i dati da leghe.fantacalcio.it ===
%PY% scripts\scarica_dati.py
if errorlevel 1 (
    echo [ERRORE] Download non riuscito: nulla e' stato pubblicato.
    echo          Se manca il token o e' scaduto (401), aggiorna FANTA_TOKEN nel file .env
    goto :fail
)

echo.
echo === 3/4 Rigenero la dashboard ===
%PY% scripts\genera_dashboard.py
if errorlevel 1 (
    echo [ERRORE] Generazione di docs\index.html non riuscita.
    goto :fail
)

echo.
echo === 4/4 Pubblico su GitHub ===
git add docs/index.html data
git diff --cached --quiet
if not errorlevel 1 (
    echo Nessuna novita' rispetto all'ultima pubblicazione: la pagina e' gia' aggiornata.
    goto :ok
)

for /f "delims=" %%g in ('%PY% -c "import json;print(sum(1 for t in json.load(open('data/calendario.json',encoding='utf-8')) if t.get('calculated')))"') do set "NGIORNATE=%%g"
for /f "delims=" %%d in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "TS=%%d"

git commit -m "Aggiornamento dati: %NGIORNATE% giornate calcolate (%TS%)"
if errorlevel 1 goto :fail
git push origin main
if errorlevel 1 (
    echo [ERRORE] git push non riuscito.
    goto :fail
)

echo.
echo Pubblicato. La pagina si aggiorna entro 1-2 minuti:
echo %PAGE_URL%

:ok
echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1

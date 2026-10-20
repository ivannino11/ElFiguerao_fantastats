"""
scarica_dati.py - Download dati della lega El Figuerao (apileague.fantacalcio.it)

Hardened version for GitHub Actions:
  * classifies every non-200 response (token, origin 403, CDN/WAF challenge or block (CloudFront/AWS WAF, Cloudflare), rate limit)
  * prints a sanitized diagnostic for each failure (never the token or proxy credentials)
  * primary client: Python standard library (urllib) with the headers of fanta_utils.headers_api()
    (verified 200 where the curl_cffi session got 403 JSON "FAIL: Request failed")
  * fallback only on CDN/WAF block: curl_cffi browser profiles (FANTA_IMPERSONATE)
  * honors Retry-After / 429 with exponential backoff + jitter
  * rotates browser profile and (optionally) proxy only when the edge blocks the runner
  * circuit breaker: stops hammering the API once auth or edge block is certain
  * writes a Markdown report to $GITHUB_STEP_SUMMARY and a JSON report for upload-artifact

Environment variables
  FANTA_TOKEN         Bearer token (required, read by fanta_utils.carica_token)
  FANTA_PROXY         optional: one proxy URL or a comma-separated list
                      (http://user:pass@host:port, socks5h://host:port). Empty = direct.
  FANTA_IMPERSONATE   curl_cffi fallback profiles, comma-separated (default: chrome,chrome146,safari184)
                      empty string = no curl_cffi fallback
  FANTA_USER_AGENT    optional UA override (default: the UA in fanta_utils.headers_api)
  FANTA_WARMUP        curl_cffi fallback only: GET leghe.fantacalcio.it first (default 0)
  FANTA_MAX_RETRIES   attempts per profile/proxy combination (default 3)
  FANTA_DIAGNOSE      1 = always log egress IP and GitHub Actions range check (default 0)

Exit codes
  0 ok | 1 partial/generic failure | 2 auth (401 or 403 from the API itself)
  3 blocked by edge (Cloudflare/WAF) | 4 rate limited
"""

import ipaddress
import itertools
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request
from urllib.parse import urlsplit

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fanta_utils import DATA_DIR, ROOT_DIR, headers_api, percorso_dati

try:  # private helper, optional: used only to log days left on the JWT
    from fanta_utils import _scadenza_jwt
except ImportError:  # pragma: no cover
    _scadenza_jwt = None

COMPETITION_ID = "619614"
LEAGUE_ID = "3595294"
BASE = "https://apileague.fantacalcio.it"
WARMUP_URL = "https://leghe.fantacalcio.it/"

IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"
MAX_RETRIES = int(os.environ.get("FANTA_MAX_RETRIES", "3"))
WARMUP = os.environ.get("FANTA_WARMUP", "0") == "1"
DIAGNOSE = os.environ.get("FANTA_DIAGNOSE", "0") == "1"
PROFILES = [p.strip() for p in os.environ.get("FANTA_IMPERSONATE", "chrome,chrome146,safari184").split(",") if p.strip()]
BACKENDS = ["urllib"] + PROFILES  # urllib first; curl_cffi profiles only if the edge blocks urllib
PROXIES = [p.strip() for p in os.environ.get("FANTA_PROXY", "").split(",") if p.strip()] or [None]
REPORT_PATH = os.path.join(os.environ.get("RUNNER_TEMP", ROOT_DIR), "diagnostica_download.json")

EXIT_OK, EXIT_GENERIC, EXIT_AUTH, EXIT_EDGE, EXIT_RATE = 0, 1, 2, 3, 4

ERRORI = []      # human-readable failures (kept for compatibility with the old log format)
DIAGNOSI = []    # structured, sanitized diagnostics


# ----------------------------------------------------------------------------
# Secrets hygiene
# ----------------------------------------------------------------------------
def _mask(value):
    """Ask the Actions runner to mask a value in every later log line."""
    if IN_ACTIONS and value:
        print(f"::add-mask::{value}")


def _proxy_label(proxy):
    """Proxy without credentials, safe to print."""
    if not proxy:
        return "diretto"
    p = urlsplit(proxy)
    return f"{p.scheme}://{p.hostname}:{p.port or ''}"


for _p in PROXIES:
    if _p:
        _mask(_p)
        _pw = urlsplit(_p).password
        _mask(_pw)

BASE_HEADERS = headers_api()  # token from FANTA_TOKEN / .env (exits early if missing/expired)
TOKEN = BASE_HEADERS.get("authorization", "")[7:]
_mask(TOKEN)

if os.environ.get("FANTA_USER_AGENT"):
    BASE_HEADERS["user-agent"] = os.environ["FANTA_USER_AGENT"]


def _redact(text):
    if not text:
        return ""
    if TOKEN:
        text = text.replace(TOKEN, "***")
    text = re.sub(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{5,}", "***JWT***", text)  # any JWT
    return text


# ----------------------------------------------------------------------------
# Response classification
# ----------------------------------------------------------------------------
def classifica(r):
    """Return one of: ok, auth, api_403, rate_limit, edge_challenge, edge_block, forbidden, server, other.

    Observed on apileague.fantacalcio.it (AWS CloudFront + WAF in front of an ASP.NET/Kestrel API):
      * missing app_key         -> 401 JSON {"code":"ATH007"}            server: Kestrel   -> auth
      * missing/invalid token   -> 403 JSON {"code":"FAIL",...}          server: CloudFront -> api_403
      * non-browser TLS client  -> 403 HTML "Request blocked"           server: CloudFront -> edge_block
    Cloudflare signals are kept so the same template works for Cloudflare-fronted sites.
    """
    h = {k.lower(): v for k, v in r.headers.items()}
    ctype = h.get("content-type", "").lower()
    server = h.get("server", "").lower()
    body = (r.text or "")[:4000].lower()
    is_cf = "cloudflare" in server or "cf-ray" in h
    is_aws = "cloudfront" in server or "cloudfront" in h.get("x-cache", "").lower() or "x-amz-cf-id" in h

    # Challenges (JS/captcha) - may arrive with 200/202/403/405
    if h.get("cf-mitigated") == "challenge" or "just a moment" in body or "/cdn-cgi/challenge-platform" in body:
        return "edge_challenge"
    if h.get("x-amzn-waf-action", "").lower() in ("challenge", "captcha"):
        return "edge_challenge"
    if r.status_code == 200:
        return "ok" if "json" in ctype or body[:1] in ("{", "[") else "edge_challenge"
    if r.status_code == 401:
        return "auth"
    if r.status_code == 429 or "error code: 1015" in body:
        return "rate_limit"
    html = "text/html" in ctype or body.lstrip().startswith(("<!doctype", "<html"))
    if r.status_code in (403, 503) and (is_cf or is_aws) and (
        html or "error code: 10" in body or "request blocked" in body or "sorry, you have been blocked" in body
    ):
        return "edge_block"                         # WAF rule: IP reputation, TLS fingerprint, geo, bot control
    if r.status_code == 403 and "json" in ctype:
        return "api_403"                            # JSON refusal: token invalid/revoked, permissions
    if r.status_code == 403:
        return "forbidden"                          # unknown 403: treat like an edge block, but log it
    if r.status_code >= 500:
        return "server"
    return "other"


def _codice(r):
    """API error code from a JSON body, e.g. FAIL or ATH007."""
    try:
        j = r.json()
        return f"{j.get('code', '?')}: {j.get('message', '')}".strip()
    except Exception:
        return "corpo non JSON"


def diagnostica(r, desc, url, kind, profilo, proxy):
    h = {k.lower(): v for k, v in r.headers.items()}
    keep = ["content-type", "server", "cf-ray", "cf-mitigated", "cf-cache-status", "retry-after",
            "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "www-authenticate", "x-cache", "x-amz-cf-pop", "x-amz-cf-id",
            "x-amzn-waf-action", "x-amzn-requestid", "x-amzn-errortype"]
    d = {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "voce": desc,
        "url": url.split("?")[0],
        "status": r.status_code,
        "tipo": kind,
        "profilo": profilo,
        "proxy": _proxy_label(proxy),
        "header": {k: h[k] for k in keep if k in h},
        "corpo": _redact((r.text or "")[:400]).replace("\n", " "),
    }
    DIAGNOSI.append(d)
    print(f"    [diag] {desc}: HTTP {d['status']} tipo={kind} profilo={profilo} via={d['proxy']}")
    for k, v in d["header"].items():
        print(f"           {k}: {v}")
    if d["corpo"]:
        print(f"           corpo: {d['corpo'][:200]}")
    return d


# ----------------------------------------------------------------------------
# Egress IP check (is the runner on GitHub/Azure ranges?)
# ----------------------------------------------------------------------------
_ip_checked = False


def controlla_ip_uscita(session):
    global _ip_checked
    if _ip_checked:
        return
    _ip_checked = True
    try:
        ip = session.get("https://api.ipify.org?format=json", timeout=10).json()["ip"]
    except Exception as e:
        print(f"    [diag] IP di uscita non determinabile ({type(e).__name__})")
        return
    in_gh = None
    try:
        import urllib.request
        req = urllib.request.Request("https://api.github.com/meta", headers={"Accept": "application/vnd.github+json", "User-Agent": "scarica-dati-diag"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.load(resp)
        addr = ipaddress.ip_address(ip)
        in_gh = any(addr in ipaddress.ip_network(n) for n in meta.get("actions", []))
    except Exception:
        pass
    esito = {True: "SI (runner GitHub/Azure: IP datacenter)", False: "no", None: "non verificabile"}[in_gh]
    print(f"    [diag] IP di uscita {ip} - nei range GitHub Actions: {esito}")
    DIAGNOSI.append({"voce": "ip_uscita", "ip": ip, "range_github_actions": in_gh})


# ----------------------------------------------------------------------------
# HTTP backends
# ----------------------------------------------------------------------------
class Risposta:
    """Minimal response object shared by the urllib and curl_cffi backends."""

    def __init__(self, status_code, headers, content):
        self.status_code = status_code
        self.headers = headers
        self.content = content or b""

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)


class SessioneUrllib:
    """Standard-library client: same headers as headers_api(), no TLS impersonation."""

    def __init__(self, headers, proxy=None, timeout=20):
        self.headers = dict(headers)
        self.timeout = timeout
        handlers = []
        if proxy:
            if not proxy.lower().startswith(("http://", "https://")):
                raise ValueError("urllib supporta solo proxy http(s)")
            handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        self.opener = urllib.request.build_opener(*handlers)

    def get(self, url, headers=None, timeout=None):
        h = dict(self.headers)
        h.update(headers or {})
        req = urllib.request.Request(url, headers=h, method="GET")
        try:
            with self.opener.open(req, timeout=timeout or self.timeout) as resp:
                return Risposta(resp.status, dict(resp.headers.items()), resp.read())
        except urllib.error.HTTPError as e:  # 4xx/5xx still carry headers and body
            try:
                body = e.read()
            except Exception:
                body = b""
            return Risposta(e.code, dict(e.headers.items()) if e.headers else {}, body)

    def close(self):
        pass


class SessioneCurl:
    """curl_cffi fallback with browser TLS impersonation (used only after an edge block)."""

    def __init__(self, profilo, headers, proxy=None, timeout=20):
        from curl_cffi import requests as curl_requests  # imported lazily: optional dependency

        h = dict(headers)
        if not os.environ.get("FANTA_USER_AGENT"):
            h.pop("user-agent", None)  # let curl_cffi send the UA that matches the profile
        kwargs = {"impersonate": profilo, "headers": h, "timeout": timeout}
        if proxy:
            kwargs["proxy"] = proxy
        self.session = curl_requests.Session(**kwargs)

    def get(self, url, headers=None, timeout=None):
        kwargs = {}
        if headers:
            kwargs["headers"] = headers
        if timeout:
            kwargs["timeout"] = timeout
        r = self.session.get(url, **kwargs)
        return Risposta(r.status_code, dict(r.headers.items()), r.content)

    def close(self):
        self.session.close()


# ----------------------------------------------------------------------------
# HTTP client with rotation and circuit breaker
# ----------------------------------------------------------------------------
class Client:
    def __init__(self):
        self.combo = list(itertools.product(PROXIES, BACKENDS))  # proxy outer: rotate backend first
        self.idx = 0
        self.session = None
        self.stop_reason = None  # "auth" | "edge" | "rate" -> circuit breaker
        self._apri()

    @property
    def proxy(self):
        return self.combo[self.idx][0]

    @property
    def profilo(self):
        return self.combo[self.idx][1]

    def _apri(self):
        if self.session:
            self.session.close()
            self.session = None
        try:
            if self.profilo == "urllib":
                self.session = SessioneUrllib(BASE_HEADERS, self.proxy)
            else:
                self.session = SessioneCurl(self.profilo, BASE_HEADERS, self.proxy)
        except Exception as e:  # curl_cffi missing, unknown profile, unsupported proxy scheme
            print(f"    [warn] {self.profilo} non disponibile ({type(e).__name__}: {_redact(str(e))}); passo al successivo")
            if not self.ruota():
                raise RuntimeError("nessun client HTTP disponibile") from e
            return
        print(f"    sessione: client={self.profilo} via={_proxy_label(self.proxy)}")
        if WARMUP and self.profilo != "urllib":
            try:
                self.session.get(WARMUP_URL, headers={"accept": "text/html,*/*"}, timeout=15)
            except Exception:
                pass
        if DIAGNOSE:
            controlla_ip_uscita(self.session)

    def ruota(self):
        """Next backend/proxy. False when exhausted."""
        if self.idx + 1 >= len(self.combo):
            return False
        self.idx += 1
        self._apri()
        return True

    @staticmethod
    def _attesa(r, tentativo):
        ra = r.headers.get("retry-after") if r is not None else None
        if ra and ra.isdigit():
            return min(int(ra), 120)
        return min(2 ** tentativo + random.uniform(0, 1.5), 60)

    def fetch_json(self, url, desc):
        if self.stop_reason:
            msg = f"{desc}: saltato (circuit breaker: {self.stop_reason})"
            print(f"Impossibile scaricare: {msg}")
            ERRORI.append(msg)
            return None

        ultimo = "nessuna risposta"
        while True:
            r, last_kind = None, None
            for tentativo in range(MAX_RETRIES):
                try:
                    r = self.session.get(url)
                except Exception as e:
                    ultimo = f"errore di rete ({type(e).__name__}): {_redact(str(e))[:200]}"
                    time.sleep(self._attesa(None, tentativo))
                    continue

                kind = classifica(r)
                if kind == "ok":
                    try:
                        return r.json()
                    except ValueError:
                        kind = "edge_challenge"

                ultimo = f"HTTP {r.status_code} {kind}"
                last_kind = kind
                diagnostica(r, desc, url, kind, self.profilo, self.proxy)

                if kind == "auth":
                    self.stop_reason = "auth"
                    ERRORI.append(f"{desc}: 401 ({_codice(r)}) token o app_key non validi -> aggiorna FANTA_TOKEN / APP_KEY")
                    return None
                if kind == "api_403":
                    self.stop_reason = "auth"
                    ERRORI.append(f"{desc}: 403 JSON dall'API ({_codice(r)}) con client {self.profilo}")
                    return None
                if kind in ("rate_limit", "server", "other"):
                    time.sleep(self._attesa(r, tentativo))
                    continue
                break  # edge_challenge / edge_block / forbidden -> change client, don't retry same one

            # edge block, or network errors with no HTTP answer: try the next client
            if last_kind in ("edge_challenge", "edge_block", "forbidden") or (r is None and last_kind is None):
                if last_kind:
                    controlla_ip_uscita(self.session)
                if self.ruota():
                    time.sleep(random.uniform(1, 3))
                    continue
                if last_kind:
                    self.stop_reason = "edge"
            elif last_kind == "rate_limit":
                self.stop_reason = "rate"
            break

        print(f"Impossibile scaricare: {desc} [{ultimo}]")
        ERRORI.append(f"{desc}: download non riuscito ({ultimo})")
        return None


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
VERDETTI = {
    "auth": "Richiesta rifiutata dall'API (401/403 JSON). Non è necessariamente il token: verifica con lo stesso token in locale prima di rinnovare FANTA_TOKEN.",
    "edge": "Blocco WAF/CDN (CloudFront/Cloudflare: IP datacenter o fingerprint): usa il runner self-hosted o un proxy (vedi runbook).",
    "rate": "Rate limit: riduci la frequenza (cron), aumenta le pause, rilancia più tardi.",
}


def scrivi_report():
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump({"errori": ERRORI, "diagnosi": DIAGNOSI}, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary or not DIAGNOSI:
        return
    righe = ["### Diagnostica download", "", "| Voce | Status | Tipo | Client | Via | edge id |", "|---|---|---|---|---|---|"]
    for d in DIAGNOSI:
        if "status" in d:
            righe.append(f"| {d['voce']} | {d['status']} | {d['tipo']} | {d['profilo']} | {d['proxy']} | {d['header'].get('cf-ray') or d['header'].get('x-amz-cf-pop', '')} |")
        elif d.get("voce") == "ip_uscita":
            righe.append(f"| IP di uscita | | GitHub range: {d['range_github_actions']} | | | |")
    with open(summary, "a", encoding="utf-8") as f:
        f.write("\n".join(righe) + "\n")


def salva(nome, dati):
    with open(percorso_dati(nome), "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=2, ensure_ascii=False)
    print(f"    [OK] Salvato {nome}")


def pausa():
    time.sleep(random.uniform(1.0, 2.0))  # polite pacing with jitter


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def scarica_tutto():
    os.makedirs(DATA_DIR, exist_ok=True)
    if _scadenza_jwt and TOKEN:
        scad = _scadenza_jwt(TOKEN)
        if scad:
            giorni = (scad - datetime.now(timezone.utc)).days
            print(f"Token valido fino al {scad:%d/%m/%Y} ({giorni} giorni)")

    c = Client()

    print(">>> 1. Scarico Elenco Squadre...")
    squadre = c.fetch_json(f"{BASE}/onboarding/v1/league/competition/teams?competitionId={COMPETITION_ID}&page=1&pageSize=50", "Squadre")
    if squadre:
        salva("squadre_fanta.json", squadre)
    pausa()

    print(">>> 2. Scarico Anagrafica e Statistiche Calciatori...")
    players = c.fetch_json(f"{BASE}/onboarding/v1/league/players?leagueId={LEAGUE_ID}", "Calciatori")
    if players:
        salva("giocatori_rose.json", players)
    pausa()

    print(">>> 3. Scarico Calendario Completo...")
    calendario = c.fetch_json(f"{BASE}/onboarding/v1/league/competition/calendar/{COMPETITION_ID}", "Calendario")
    if calendario:
        salva("calendario.json", calendario)
        print(">>> 4. Scarico Formazioni e Voti delle giornate calcolate...")
        for turno in calendario:
            if not turno.get("calculated", False) or c.stop_reason:
                continue
            g_lega, g_serie_a = turno.get("matchDay"), turno.get("championshipMatchDay")
            pausa()
            lineup = c.fetch_json(f"{BASE}/gaming/v1/teamLineup/{COMPETITION_ID}/{g_lega}/{g_serie_a}",
                                  f"Formazioni Giornata {g_lega} (Serie A {g_serie_a})")
            if lineup:
                salva(f"lineup_giornata_{g_lega}.json", lineup)

    scrivi_report()
    if ERRORI:
        print("\nDownload NON completato, errori:")
        for e in ERRORI:
            print(f"  - {e}")
        if c.stop_reason:
            print(f"\nCausa probabile: {VERDETTI[c.stop_reason]}")
            if IN_ACTIONS:
                print(f"::error title=Download fallito ({c.stop_reason})::{VERDETTI[c.stop_reason]}")
        return {"auth": EXIT_AUTH, "edge": EXIT_EDGE, "rate": EXIT_RATE}.get(c.stop_reason, EXIT_GENERIC)
    print("\nDownload completato con successo!")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(scarica_tutto())

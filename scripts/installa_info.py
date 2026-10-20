"""Installa pop-up informativi nel generatore e nella pagina, senza scaricare dati."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = [
    [r"fantavoto medio.*panchina|fantamedia.*panchina", "Fantavoto medio panchina", "Media dei fantavoti dei soli giocatori conteggiati come rimpianti, non di tutta la panchina."],
    [r"gol.*panchina|gol.*panca", "Gol in panchina", "Gol, compresi i rigori, dei giocatori rimasti in panchina senza subentrare nelle giornate disponibili. Non equivalgono automaticamente a punti persi in classifica."],
    [r"assist.*panchina|assist.*panca", "Assist in panchina", "Assist dei giocatori rimasti in panchina senza subentrare nelle giornate disponibili."],
    [r"rimpiant", "Rimpianti", "Giocatori rimasti in panchina, senza subentrare, con gol, assist o fantavoto almeno 7. Ogni presenza in giornate diverse conta separatamente. La classifica ordina per gol, poi assist e numero di rimpianti."],
    [r"diff.*punt|saldo.*punt", "Differenza punti What-if", "Punti simulati meno punti reali: positivo significa più punti nella simulazione, negativo meno. Anche gli avversari vengono ottimizzati."],
    [r"fortun|sfortun", "Fortuna nella simulazione", "Etichetta basata sul confronto fra punti simulati e reali: sfortunato se la simulazione assegna più punti, fortunato se ne assegna meno. Non misura la fortuna in modo indipendente."],
    [r"what.?if|best.?xi|formazione.*perfett|formazione.*ideal", "Simulazione What-if", "Migliora tutte le squadre con panchinari dello stesso ruolo e fantavoto superiore, senza cambiare modulo. Anche gli avversari sono ottimizzati. Modificatori invariati: primo gol a 66 fantapunti, poi uno ogni 6."],
    [r"win.?rate|percentuale.*vittor", "Percentuale di vittorie", "Vittorie con il modulo divise per i suoi utilizzi, in percentuale. Considera tutte le squadre nelle giornate disponibili."],
    [r"modul", "Rendimento dei moduli", "Confronta utilizzi, media dei fantapunti e risultati di tutte le squadre con ciascun modulo. Ordina per fantapunti medi: non dimostra che il modulo causi risultati migliori."],
    [r"affar", "Affare della rosa", "Giocatore della rosa attuale con la fantamedia più alta fra quelli costati al massimo 10 crediti e con almeno una presenza registrata. Non è un rapporto rendimento/prezzo."],
    [r"mvp", "MVP della rosa", "Giocatore della rosa attuale con la fantamedia più alta e almeno una presenza registrata. Il calcolo include le presenze disponibili nelle formazioni, anche in panchina."],
    [r"bomber|marcator", "Marcatori", "Gol registrati nelle formazioni disponibili, compresi i rigori, anche quando il giocatore era in panchina. I giocatori sono associati alle rose attuali."],
    [r"assistman|top.*assist", "Assistman", "Assist registrati nelle formazioni disponibili, anche quando il giocatore era in panchina. I giocatori sono associati alle rose attuali."],
    [r"bad.?boy|cattiv", "Disciplina", "Cartellini registrati nelle formazioni disponibili, anche in panchina. L'ordine privilegia le espulsioni, poi le ammonizioni: non somma semplicemente i cartellini."],
    [r"crediti.*spes", "Crediti spesi", "Crediti spesi riportati dall'API per la squadra: non sono una valutazione del rendimento della rosa."],
    [r"crediti.*residu", "Crediti residui", "Crediti ancora disponibili riportati dall'API per la squadra."],
    [r"rose.*finanz|finanz.*rose", "Rose e finanze", "Rosa attuale, costi, quotazioni e crediti. In questa vista la fantamedia proviene dall'anagrafica API, non dal ricalcolo delle sole giornate della dashboard."]
]
JS = r"""(() => {
'use strict';
if(window.fantaInfoInstalled)return;
window.fantaInfoInstalled=true;
const topics=__TOPICS__;
const style=document.createElement('style');
style.textContent=`
.fanta-info-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;min-width:36px;vertical-align:middle;margin-left:8px;border:1px solid #818cf866;border-radius:50%;background:#6366f118;color:#c7d2fe;font:700 16px Georgia,serif;cursor:pointer;text-transform:none;letter-spacing:0}
.fanta-info-btn:hover{background:#6366f144}.fanta-info-btn:focus-visible,.fanta-info-close:focus-visible{outline:3px solid #a5b4fc;outline-offset:3px}
#fanta-info-dialog{position:fixed;inset:0;margin:auto;width:min(480px,calc(100vw - 32px));max-height:calc(100dvh - 40px);overflow:auto;padding:26px;border:1px solid #818cf866;border-radius:20px;background:linear-gradient(145deg,#1d2540,#121722);color:#f8fafc;box-shadow:0 24px 90px #0009;font-family:inherit}
#fanta-info-dialog::backdrop{background:#050814b8;backdrop-filter:blur(5px)}
#fanta-info-dialog h2{padding-right:36px;font-size:1.15rem;margin:0 0 14px;line-height:1.4;color:#e0e7ff}
#fanta-info-dialog p{font-size:.95rem;line-height:1.7;color:#cbd5e1;margin:0}
.fanta-info-close{position:absolute;right:12px;top:10px;width:40px;height:40px;border:0;border-radius:10px;background:#ffffff0d;color:#fff;font-size:24px;cursor:pointer}
@media(prefers-reduced-motion:no-preference){#fanta-info-dialog[open]{animation:fi .16s ease-out}@keyframes fi{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}}
`;
document.head.append(style);
const dialog=document.createElement('dialog');
dialog.id='fanta-info-dialog';
dialog.setAttribute('aria-labelledby','fanta-info-title');
dialog.setAttribute('aria-describedby','fanta-info-text');
dialog.innerHTML='<button type="button" class="fanta-info-close" aria-label="Chiudi spiegazione">×</button><h2 id="fanta-info-title"></h2><p id="fanta-info-text"></p>';
document.body.append(dialog);
let opener=null;
dialog.querySelector('button').onclick=()=>dialog.close();
dialog.addEventListener('close',()=>{if(opener?.isConnected)opener.focus()});
dialog.addEventListener('click',e=>{if(e.target!==dialog)return;const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()});
function scan(){
 document.querySelectorAll('.hero-label,.table-header h2,.table-header h3,.section-title,.chart-title,.tab-pane h2,.tab-pane h3').forEach(el=>{
  if(el.querySelector('.fanta-info-btn'))return;
  const label=el.textContent.trim();
  const topic=topics.find(t=>new RegExp(t[0],'i').test(label));
  if(!topic)return;
  const b=document.createElement('button');b.type='button';b.className='fanta-info-btn';b.textContent='i';
  b.setAttribute('aria-label','Spiegazione: '+label);b.setAttribute('aria-haspopup','dialog');
  b.onclick=e=>{e.stopPropagation();opener=b;dialog.querySelector('h2').textContent=topic[1];dialog.querySelector('p').textContent=topic[2];dialog.showModal()};
  el.append(b);
 });
}
scan();let queued=false;
new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;scan()})}).observe(document.body,{childList:true,subtree:true});
})();"""
START = '<!-- fanta-info:start -->'
END = '<!-- fanta-info:end -->'
SNIPPET = START + '\n<script>\n' + JS.replace('__TOPICS__', json.dumps(TOPICS, ensure_ascii=False)) + '\n</script>\n' + END


def clean(text):
    return re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', '', text, flags=re.S)


def install_generator(source):
    source = clean(source)
    tree = ast.parse(source)
    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'html_content' for t in node.targets) and isinstance(node.value, ast.JoinedStr):
            candidates.append(node.value)
    if len(candidates) != 1:
        raise ValueError('Template html_content non univoco: nessun file modificato')
    node = candidates[0]
    lines = source.splitlines(keepends=True)
    start = sum(map(len, lines[:node.lineno-1])) + len(lines[node.lineno-1].encode()[:node.col_offset].decode())
    end = sum(map(len, lines[:node.end_lineno-1])) + len(lines[node.end_lineno-1].encode()[:node.end_col_offset].decode())
    template = source[start:end]
    if template.count('</body>') != 1:
        raise ValueError('Chiusura body non univoca')
    escaped = SNIPPET.replace('{', '{{').replace('}', '}}').replace(chr(92), chr(92)*2)
    updated = source[:start] + template.replace('</body>', escaped + '\n</body>') + source[end:]
    ast.parse(updated)
    return updated


def main():
    generator = ROOT / 'scripts/genera_dashboard.py'
    page = ROOT / 'docs/index.html'
    source = install_generator(generator.read_text(encoding='utf-8'))
    html = clean(page.read_text(encoding='utf-8'))
    if html.count('</body>') != 1:
        raise ValueError('HTML inatteso: nessun file modificato')
    html = html.replace('</body>', SNIPPET + '\n</body>')
    generator.write_text(source, encoding='utf-8')
    page.write_text(html, encoding='utf-8')
    print('Info installate nel generatore e nella pagina. Dati e formule invariati.')


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""Conselheiro — recomenda LLM por tarefa (Vercel serverless, WSGI puro)."""
import os, json, hashlib, time
import urllib.request, urllib.error

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ADVISOR_MODEL = "deepseek/deepseek-chat-v3"

MODELS = [
    {"id": "openai/gpt-4o", "label": "GPT-4o", "vendor": "OpenAI", "ctx": "128k", "out": 10.0, "in": 2.5,
     "scores": {"code":9,"reason":9,"write":9,"long":8,"vision":10,"audio":10,"multi":10,"price_eff":5}},
    {"id": "openai/gpt-4o-mini", "label": "GPT-4o mini", "vendor": "OpenAI", "ctx": "128k", "out": 0.6, "in": 0.15,
     "scores": {"code":8,"reason":8,"write":8,"long":7,"vision":8,"audio":8,"multi":8,"price_eff":9}},
    {"id": "openai/o3", "label": "o3", "vendor": "OpenAI", "ctx": "200k", "out": 60.0, "in": 15.0,
     "scores": {"code":10,"reason":10,"write":8,"long":9,"vision":9,"audio":7,"multi":8,"price_eff":3}},
    {"id": "anthropic/claude-sonnet-4", "label": "Claude Sonnet 4", "vendor": "Anthropic", "ctx": "200k", "out": 15.0, "in": 3.0,
     "scores": {"code":9,"reason":10,"write":10,"long":10,"vision":9,"audio":8,"multi":9,"price_eff":6}},
    {"id": "anthropic/claude-opus-4", "label": "Claude Opus 4", "vendor": "Anthropic", "ctx": "200k", "out": 75.0, "in": 15.0,
     "scores": {"code":9,"reason":10,"write":10,"long":10,"vision":9,"audio":8,"multi":9,"price_eff":3}},
    {"id": "google/gemini-2.5-pro", "label": "Gemini 2.5 Pro", "vendor": "Google", "ctx": "1M+", "out": 10.0, "in": 1.25,
     "scores": {"code":9,"reason":10,"write":9,"long":10,"vision":10,"audio":10,"multi":10,"price_eff":7}},
    {"id": "google/gemini-2.5-flash", "label": "Gemini 2.5 Flash", "vendor": "Google", "ctx": "1M+", "out": 0.6, "in": 0.075,
     "scores": {"code":8,"reason":8,"write":8,"long":9,"vision":9,"audio":9,"multi":9,"price_eff":10}},
    {"id": "meta-llama/llama-4-maverick", "label": "Llama 4 Maverick", "vendor": "Meta", "ctx": "1M", "out": 0.85, "in": 0.20,
     "scores": {"code":8,"reason":8,"write":7,"long":9,"vision":9,"audio":7,"multi":9,"price_eff":9}},
    {"id": "meta-llama/llama-4-scout", "label": "Llama 4 Scout", "vendor": "Meta", "ctx": "10M", "out": 0.30, "in": 0.07,
     "scores": {"code":7,"reason":7,"write":7,"long":10,"vision":8,"audio":7,"multi":8,"price_eff":10}},
    {"id": "qwen/qwen-3-235b-a22b-instruct", "label": "Qwen 3 235B", "vendor": "Alibaba", "ctx": "128k", "out": 0.60, "in": 0.15,
     "scores": {"code":9,"reason":9,"write":8,"long":7,"vision":8,"audio":7,"multi":8,"price_eff":9}},
    {"id": "deepseek/deepseek-chat-v3", "label": "DeepSeek V3", "vendor": "DeepSeek", "ctx": "128k", "out": 0.80, "in": 0.15,
     "scores": {"code":9,"reason":8,"write":8,"long":7,"vision":7,"audio":6,"multi":7,"price_eff":10}},
    {"id": "deepseek/deepseek-r1", "label": "DeepSeek R1", "vendor": "DeepSeek", "ctx": "128k", "out": 2.20, "in": 0.55,
     "scores": {"code":10,"reason":10,"write":6,"long":7,"vision":6,"audio":5,"multi":6,"price_eff":7}},
    {"id": "mistralai/mistral-large-latest", "label": "Mistral Large", "vendor": "Mistral", "ctx": "128k", "out": 4.0, "in": 1.0,
     "scores": {"code":8,"reason":8,"write":8,"long":7,"vision":8,"audio":7,"multi":8,"price_eff":7}},
    {"id": "x-ai/grok-3", "label": "Grok 3", "vendor": "xAI", "ctx": "131k", "out": 15.0, "in": 3.0,
     "scores": {"code":8,"reason":9,"write":8,"long":8,"vision":8,"audio":7,"multi":8,"price_eff":5}},
    {"id": "google/gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash Lite", "vendor": "Google", "ctx": "1M+", "out": 0.20, "in": 0.025,
     "scores": {"code":7,"reason":7,"write":7,"long":9,"vision":8,"audio":8,"multi":8,"price_eff":10}},
]

CSS = """
:root{--canvas:#010102;--s1:#0f1011;--s2:#141516;--ink:#f7f8f8;--ink-muted:#d0d6e0;--ink-subtle:#8a8f98;--ink-tertiary:#62666d;
--hairline:#23252a;--hairline-strong:#34343a;--primary:#5e6ad2;--primary-hover:#828fff;--primary-focus:#5e69d1;--on-primary:#fff;
--r-md:8px;--r-lg:12px;--r-pill:9999px;--t-d-md:40px;--t-card:22px;--t-body-lg:18px;--t-body:16px;--t-body-sm:14px;--t-cap:12px;--t-eye:13px}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{margin:0;padding:0}
body{background:var(--canvas);color:var(--ink);font:400 var(--t-body)/1.5 -apple-system,system-ui,Segoe UI,Roboto,sans-serif;min-height:100vh}
.wrap{max-width:1200px;margin:0 auto;padding:96px 32px}
h1{font-size:var(--t-d-md);font-weight:600;letter-spacing:-1px;line-height:1.15;margin:0 0 8px}
.sub{color:var(--ink-muted);font-size:var(--t-body-lg);margin:0 0 48px}
.eyebrow{font-size:var(--t-eye);font-weight:500;letter-spacing:.4px;text-transform:uppercase;color:var(--ink-subtle);margin:0 0 12px}
.card{background:var(--s1);border:1px solid var(--hairline);border-radius:var(--r-lg);padding:24px}
.input-row{display:flex;gap:12px;align-items:flex-start}
textarea{flex:1;min-height:88px;resize:vertical;background:var(--s1);color:var(--ink);border:1px solid var(--hairline);border-radius:var(--r-md);padding:10px 12px;font:400 var(--t-body)/1.5 inherit;outline:none}
textarea:focus{border-color:var(--primary-focus);box-shadow:0 0 0 2px rgba(94,106,210,.5)}
.btn{display:inline-flex;align-items:center;background:var(--primary);color:var(--on-primary);border:0;border-radius:var(--r-md);padding:8px 14px;font:500 14px/1.2 inherit;cursor:pointer;min-height:36px}
.btn:hover{background:var(--primary-hover)}.btn:disabled{opacity:.6;cursor:default}
.chip{display:inline-block;background:var(--s2);color:var(--ink-muted);font-size:var(--t-cap);padding:2px 8px;border-radius:var(--r-pill)}
.examples{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.ex{background:var(--s1);border:1px solid var(--hairline);color:var(--ink-muted);border-radius:var(--r-pill);padding:4px 12px;font-size:var(--t-cap);cursor:pointer}
.ex:hover{background:var(--s2);border-color:var(--hairline-strong);color:var(--ink)}
.kbd{font-family:ui-monospace,Menlo,monospace;font-size:var(--t-cap);background:var(--s2);border:1px solid var(--hairline);border-radius:4px;padding:1px 6px;color:var(--ink-muted)}
.results{margin-top:32px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:1024px){.results{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.results{grid-template-columns:1fr}.input-row{flex-direction:column}.wrap{padding:48px 20px}}
.r-card{background:var(--s1);border:1px solid var(--hairline);border-radius:var(--r-lg);padding:24px;display:flex;flex-direction:column;gap:14px;position:relative}
.r-card.top{background:var(--s2);border-color:var(--hairline-strong)}
.badge-top{position:absolute;top:-10px;left:24px;background:var(--primary);color:var(--on-primary);font-size:var(--t-cap);font-weight:600;padding:3px 10px;border-radius:var(--r-pill)}
.r-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.r-title{font-size:var(--t-card);font-weight:500;letter-spacing:-.4px;margin:0}
.r-vendor{font-size:var(--t-cap);color:var(--ink-subtle);letter-spacing:.4px;text-transform:uppercase}
.r-score-num{font-size:36px;font-weight:600;letter-spacing:-1px;line-height:1}
.r-score-out{color:var(--ink-subtle);font-size:var(--t-body-sm)}
.r-pros,.r-cons{font-size:var(--t-body-sm);line-height:1.55}
.r-pros b,.r-cons b{color:var(--ink);font-weight:600;display:block;margin-bottom:4px;font-size:var(--t-cap);text-transform:uppercase;letter-spacing:.4px}
.r-pros{color:var(--ink-muted)}.r-cons{color:var(--ink-subtle)}
.r-meta{display:flex;flex-wrap:wrap;gap:6px;font-size:var(--t-cap);color:var(--ink-subtle);border-top:1px solid var(--hairline);padding-top:12px}
.skel{background:var(--s2);border-radius:var(--r-md);height:14px;margin:4px 0;animation:sh 1.2s ease-in-out infinite}
@keyframes sh{0%,100%{opacity:.55}50%{opacity:1}}
.empty{color:var(--ink-subtle);text-align:center;padding:48px 16px;border:1px dashed var(--hairline);border-radius:var(--r-lg)}
.cta-banner{background:var(--s1);border:1px solid var(--hairline);border-radius:var(--r-lg);padding:48px;text-align:center;margin-top:48px}
footer{margin-top:96px;text-align:center;color:var(--ink-tertiary);font-size:var(--t-cap)}
a.f{color:var(--ink-subtle);text-decoration:none;border-bottom:1px solid var(--hairline)}
"""

HTML = """<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Conselheiro · qual LLM pro seu trabalho?</title><style>__CSS__</style></head><body>
<div class="wrap">
<p class="eyebrow">conselheiro</p>
<h1>qual llm pra esse trabalho?</h1>
<p class="sub">descreve o que vc quer fazer. a gente olha 15 modelos e recomenda os 3 melhores, com motivo, prós, contras e preço.</p>
<div class="card">
<div class="input-row"><textarea id="task" placeholder="ex: transcrever e resumir reunião de 1h em português; criar site em react; analisar código python..." autofocus></textarea></div>
<div class="examples">
<span class="ex" data-q="resumir 50 artigos acadêmicos em português, gerar um sumário executivo">resumir 50 artigos</span>
<span class="ex" data-q="criar um site em react com tailwind, formulário, login e dashboard">site em react</span>
<span class="ex" data-q="transcrever áudio de reunião de 1h e gerar ata estruturada em pt-br">transcrever reunião</span>
<span class="ex" data-q="analisar código python de 10k linhas e achar bugs de performance">análise de código</span>
<span class="ex" data-q="responder perguntas sobre um PDF de 800 páginas, citando trechos">PDF de 800 páginas</span>
</div>
<div class="input-row" style="margin-top:16px;align-items:center">
<button class="btn" id="go">recomendar</button>
<span class="kbd" style="margin-left:8px">ctrl+enter</span>
<span id="status" style="margin-left:auto;color:var(--ink-subtle);font-size:var(--t-cap)"></span>
</div></div>
<div id="results" class="results"></div>
<div class="cta-banner"><p class="eyebrow" style="margin:0 0 12px">como funciona</p>
<p style="margin:0 0 16px">15 modelos com notas por categoria (código, raciocínio, escrita, contexto longo, visão, áudio, multimodal) e preço. um modelo advisor ranqueia a sua tarefa específica e justifica.</p>
<span class="chip">15 modelos · top 3 · prós e contras</span></div>
</div>
<footer>conselheiro · openrouter</footer>
<script>
const $=s=>document.querySelector(s),res=$('#results'),st=$('#status');
document.querySelectorAll('.ex').forEach(b=>b.addEventListener('click',()=>{$('#task').value=b.dataset.q;rec()}));
$('#task').addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='Enter')rec()});
$('#go').addEventListener('click',rec);
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function card(m,top){const pros=(m.pros||[]).map(p=>`<div>${esc(p)}</div>`).join(''),cons=(m.cons||[]).map(c=>`<div>${esc(c)}</div>`).join('');
return `<div class="r-card ${top?'top':''}">${top?'<div class="badge-top">recomendado</div>':''}
<div class="r-head"><div><p class="r-vendor">${esc(m.vendor)}</p><p class="r-title">${esc(m.label)}</p></div>
<div><span class="r-score-num">${m.score}</span><span class="r-score-out">/10</span></div></div>
<div class="r-pros"><b>por que</b>${pros}</div><div class="r-cons"><b>cuidado</b>${cons}</div>
<div class="r-meta">${esc(m.vendor)} · ${esc(m.ctx)} ctx · $${m.out}/M out · $${m.in}/M in</div></div>`}
function skel(){return [0,1,2].map(()=>`<div class="r-card"><div class="skel" style="width:60%"></div><div class="skel" style="width:90%"></div><div class="skel" style="width:80%"></div></div>`).join('')}
async function rec(){const q=$('#task').value.trim();if(!q){$('#task').focus();return}
res.innerHTML=skel();st.textContent='analisando...';$('#go').disabled=true;
try{const r=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:q})});
const j=await r.json();if(j.error)throw new Error(j.error);
res.innerHTML=j.picks.map((m,i)=>card(m,i===0)).join('');st.textContent='';}
catch(e){res.innerHTML=`<div class="empty" style="grid-column:1/-1">erro: ${esc(e.message)}</div>`;st.textContent=''}
finally{$('#go').disabled=false}}
</script></body></html>"""

SYSTEM = """Voce e um advisor de LLMs. O usuario descreve uma tarefa. Voce recebe um catalogo de modelos com notas (1-10) por categoria e preco.
Escolha os 3 melhores modelos pra essa tarefa. Justifique cada um com 2-3 PROS e 2 CONS curtos (uma frase cada, em portugues). Use o preco como variavel (prefira custo-beneficio se o user nao citou orcamento).
Responda APENAS em JSON valido com este schema, sem markdown:
{"picks":[{"id":"<model_id>","score":<1-10 com 1 casa>,"pros":["..."],"cons":["..."]}]}
Ordem: do melhor pro pior."""

_cache = {}

def call_openrouter(task):
    lines = [f'- {m["id"]} | {m["label"]} ({m["vendor"]}, ctx {m["ctx"]}, ${m["out"]}/M out, ${m["in"]}/M in) | ' +
             " ".join(f'{k}:{v}' for k, v in m["scores"].items()) for m in MODELS]
    body = {
        "model": ADVISOR_MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"TAREFA DO USUARIO: {task}\n\nCATALOGO:\n" + "\n".join(lines)}],
        "temperature": 0.2, "max_tokens": 900,
    }
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    txt = (msg.get("content") or "").strip()
    if txt.startswith("```"):
        txt = txt.split("\n", 1)[1]
        if txt.endswith("```"): txt = txt[:-3]
    return json.loads(txt)["picks"]

def enrich(picks):
    by_id = {m["id"]: m for m in MODELS}
    out = []
    for p in picks:
        m = by_id.get(p.get("id"))
        if m:
            out.append({"id": m["id"], "label": m["label"], "vendor": m["vendor"], "ctx": m["ctx"],
                        "out": m["out"], "in": m["in"], "score": float(p.get("score", 7)),
                        "pros": (p.get("pros") or [])[:3], "cons": (p.get("cons") or [])[:3]})
    return out

def app(environ, start_response):
    path = environ.get("PATH_INFO", "/").rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/" and method == "GET":
        body = HTML.replace("__CSS__", CSS).encode("utf-8")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]

    if path == "/api" and method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
            raw = environ["wsgi.input"].read(length) or b"{}"
            try: req = json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError: req = json.loads(raw.decode("latin-1"))
            task = (req.get("task") or "").strip()
            if not task:
                raise ValueError("tarefa vazia")
            if not OPENROUTER_KEY:
                raise ValueError("OPENROUTER_API_KEY nao configurada no servidor")
            key = hashlib.sha256(task.lower().encode()).hexdigest()
            hit = _cache.get(key)
            if hit and hit["ts"] > time.time() - 86400:
                payload = {"picks": hit["picks"], "cached": True}
            else:
                picks = enrich(call_openrouter(task))
                if not picks: raise ValueError("advisor nao retornou picks validos")
                _cache[key] = {"ts": time.time(), "picks": picks}
                payload = {"picks": picks, "cached": False}
            status, code = "200 OK", 200
        except urllib.error.HTTPError as e:
            try: detail = e.read().decode("utf-8", "replace")[:200]
            except Exception: detail = ""
            payload = {"error": f"openrouter {e.code}: {detail}"}
            status, code = "502 Bad Gateway", 502
        except Exception as e:
            payload = {"error": f"{type(e).__name__}: {e}"}
            status, code = "500 Internal Server Error", 500
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
        return [body]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"not found"]

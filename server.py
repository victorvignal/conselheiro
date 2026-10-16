"""
LLM advisor: recomenda modelos pra uma tarefa.
- Front: Linear design (dark, lavender #5e6ad2, surface ladder).
- Backend: OpenRouter, com lista curada de modelos + chamada que ranqueia.
- Lê a chave de OPENROUTER_API_KEY no env.
- Salva cache das recomendacoes em /tmp pra nao estourar a cota.
"""
import os, json, hashlib, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import urllib.request, urllib.error

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CACHE_PATH = "/tmp/llm_advisor_cache.json"
PORT = 8765

# 15 modelos mais usados hoje, com notas por categoria (1-10).
# Tarefa: code, reasoning, writing, long_ctx, vision, audio, multimodal, price_eff.
MODELS = [
    # id OpenRouter, label, empresa, ctx, saida $/M, entrada $/M, notas (code, reason, write, long, vision, audio, multi, price_eff)
    {"id": "openai/gpt-4o",                      "label": "GPT-4o",                       "vendor": "OpenAI",      "ctx": "128k",  "out": 10.0, "in": 2.5,
     "scores": {"code":9,"reason":9,"write":9,"long":8,"vision":10,"audio":10,"multi":10,"price_eff":5}},
    {"id": "openai/gpt-4o-mini",                 "label": "GPT-4o mini",                  "vendor": "OpenAI",      "ctx": "128k",  "out": 0.6, "in": 0.15,
     "scores": {"code":8,"reason":8,"write":8,"long":7,"vision":8,"audio":8,"multi":8,"price_eff":9}},
    {"id": "openai/o3",                          "label": "o3",                            "vendor": "OpenAI",      "ctx": "200k",  "out": 60.0, "in": 15.0,
     "scores": {"code":10,"reason":10,"write":8,"long":9,"vision":9,"audio":7,"multi":8,"price_eff":3}},
    {"id": "anthropic/claude-sonnet-4",          "label": "Claude Sonnet 4",              "vendor": "Anthropic",   "ctx": "200k",  "out": 15.0, "in": 3.0,
     "scores": {"code":9,"reason":10,"write":10,"long":10,"vision":9,"audio":8,"multi":9,"price_eff":6}},
    {"id": "anthropic/claude-opus-4",            "label": "Claude Opus 4",                "vendor": "Anthropic",   "ctx": "200k",  "out": 75.0, "in": 15.0,
     "scores": {"code":9,"reason":10,"write":10,"long":10,"vision":9,"audio":8,"multi":9,"price_eff":3}},
    {"id": "google/gemini-2.5-pro",              "label": "Gemini 2.5 Pro",               "vendor": "Google",      "ctx": "1M+",   "out": 10.0, "in": 1.25,
     "scores": {"code":9,"reason":10,"write":9,"long":10,"vision":10,"audio":10,"multi":10,"price_eff":7}},
    {"id": "google/gemini-2.5-flash",            "label": "Gemini 2.5 Flash",             "vendor": "Google",      "ctx": "1M+",   "out": 0.6, "in": 0.075,
     "scores": {"code":8,"reason":8,"write":8,"long":9,"vision":9,"audio":9,"multi":9,"price_eff":10}},
    {"id": "meta-llama/llama-4-maverick",        "label": "Llama 4 Maverick",             "vendor": "Meta",        "ctx": "1M",    "out": 0.85, "in": 0.20,
     "scores": {"code":8,"reason":8,"write":7,"long":9,"vision":9,"audio":7,"multi":9,"price_eff":9}},
    {"id": "meta-llama/llama-4-scout",           "label": "Llama 4 Scout",                "vendor": "Meta",        "ctx": "10M",   "out": 0.30, "in": 0.07,
     "scores": {"code":7,"reason":7,"write":7,"long":10,"vision":8,"audio":7,"multi":8,"price_eff":10}},
    {"id": "qwen/qwen-3-235b-a22b-instruct",     "label": "Qwen 3 235B",                  "vendor": "Alibaba",     "ctx": "128k",  "out": 0.60, "in": 0.15,
     "scores": {"code":9,"reason":9,"write":8,"long":7,"vision":8,"audio":7,"multi":8,"price_eff":9}},
    {"id": "deepseek/deepseek-chat-v3",          "label": "DeepSeek V3",                  "vendor": "DeepSeek",    "ctx": "128k",  "out": 0.80, "in": 0.15,
     "scores": {"code":9,"reason":8,"write":8,"long":7,"vision":7,"audio":6,"multi":7,"price_eff":10}},
    {"id": "deepseek/deepseek-r1",               "label": "DeepSeek R1",                  "vendor": "DeepSeek",    "ctx": "128k",  "out": 2.20, "in": 0.55,
     "scores": {"code":10,"reason":10,"write":6,"long":7,"vision":6,"audio":5,"multi":6,"price_eff":7}},
    {"id": "mistralai/mistral-large-latest",     "label": "Mistral Large",                "vendor": "Mistral",     "ctx": "128k",  "out": 4.0, "in": 1.0,
     "scores": {"code":8,"reason":8,"write":8,"long":7,"vision":8,"audio":7,"multi":8,"price_eff":7}},
    {"id": "x-ai/grok-3",                        "label": "Grok 3",                       "vendor": "xAI",         "ctx": "131k",  "out": 15.0, "in": 3.0,
     "scores": {"code":8,"reason":9,"write":8,"long":8,"vision":8,"audio":7,"multi":8,"price_eff":5}},
    {"id": "google/gemini-2.5-flash-lite",       "label": "Gemini 2.5 Flash Lite",        "vendor": "Google",      "ctx": "1M+",   "out": 0.20, "in": 0.025,
     "scores": {"code":7,"reason":7,"write":7,"long":9,"vision":8,"audio":8,"multi":8,"price_eff":10}},
]

CSS = """
:root{
  --canvas:#010102; --s1:#0f1011; --s2:#141516; --s3:#18191a; --s4:#191a1b;
  --ink:#f7f8f8; --ink-muted:#d0d6e0; --ink-subtle:#8a8f98; --ink-tertiary:#62666d;
  --hairline:#23252a; --hairline-strong:#34343a; --hairline-tertiary:#3e3e44;
  --primary:#5e6ad2; --primary-hover:#828fff; --primary-focus:#5e69d1; --on-primary:#fff;
  --ok:#27a644;
  --r-xs:4px; --r-sm:6px; --r-md:8px; --r-lg:12px; --r-xl:16px; --r-pill:9999px;
  --t-d-xl:80px; --t-d-lg:56px; --t-d-md:40px; --t-head:28px; --t-card:22px; --t-sub:20px;
  --t-body-lg:18px; --t-body:16px; --t-body-sm:14px; --t-cap:12px; --t-btn:14px; --t-eye:13px;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0}
body{background:var(--canvas);color:var(--ink);font:400 var(--t-body)/1.5 -apple-system,system-ui,Segoe UI,Roboto,sans-serif;min-height:100vh}
.wrap{max-width:1200px;margin:0 auto;padding:96px 32px}
h1{font-size:var(--t-d-md);font-weight:600;letter-spacing:-1px;line-height:1.15;margin:0 0 8px;color:var(--ink)}
.sub{color:var(--ink-muted);font-size:var(--t-body-lg);margin:0 0 48px;letter-spacing:-0.1px}
.eyebrow{font-size:var(--t-eye);font-weight:500;letter-spacing:0.4px;text-transform:uppercase;color:var(--ink-subtle);margin:0 0 12px}
.card{background:var(--s1);border:1px solid var(--hairline);border-radius:var(--r-lg);padding:24px}
.cta-banner{background:var(--s1);border:1px solid var(--hairline);border-radius:var(--r-lg);padding:48px;text-align:center}
.input-row{display:flex;gap:12px;align-items:flex-start}
textarea{flex:1;min-height:88px;resize:vertical;background:var(--s1);color:var(--ink);
  border:1px solid var(--hairline);border-radius:var(--r-md);padding:10px 12px;
  font:400 var(--t-body)/1.5 inherit;letter-spacing:-0.05px;outline:none;transition:border-color .15s,box-shadow .15s}
textarea:focus{border-color:var(--primary-focus);box-shadow:0 0 0 2px rgba(94,106,210,.5)}
.btn{display:inline-flex;align-items:center;justify-content:center;background:var(--primary);color:var(--on-primary);
  border:0;border-radius:var(--r-md);padding:8px 14px;font:500 var(--t-btn)/1.2 inherit;letter-spacing:0;cursor:pointer;
  transition:background .15s;min-height:36px}
.btn:hover{background:var(--primary-hover)}
.btn:active{background:var(--primary-focus)}
.btn.ghost{background:var(--s1);color:var(--ink);border:1px solid var(--hairline)}
.btn.ghost:hover{background:var(--s2);border-color:var(--hairline-strong)}
.chip{display:inline-block;background:var(--s2);color:var(--ink-muted);
  font-size:var(--t-cap);padding:2px 8px;border-radius:var(--r-pill)}
.results{margin-top:32px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media (max-width:1024px){.results{grid-template-columns:repeat(2,1fr)}}
@media (max-width:640px){.results{grid-template-columns:1fr}.input-row{flex-direction:column}.wrap{padding:48px 20px}}
.r-card{background:var(--s1);border:1px solid var(--hairline);border-radius:var(--r-lg);padding:24px;display:flex;flex-direction:column;gap:14px;position:relative}
.r-card.top{background:var(--s2);border-color:var(--hairline-strong)}
.badge-top{position:absolute;top:-10px;left:24px;background:var(--primary);color:var(--on-primary);
  font-size:var(--t-cap);font-weight:600;padding:3px 10px;border-radius:var(--r-pill)}
.r-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.r-title{font-size:var(--t-card);font-weight:500;letter-spacing:-0.4px;color:var(--ink);margin:0}
.r-vendor{font-size:var(--t-cap);color:var(--ink-subtle);letter-spacing:0.4px;text-transform:uppercase}
.r-score{display:flex;align-items:baseline;gap:6px}
.r-score-num{font-size:36px;font-weight:600;letter-spacing:-1px;color:var(--ink);line-height:1}
.r-score-out{color:var(--ink-subtle);font-size:var(--t-body-sm)}
.r-pros,.r-cons{font-size:var(--t-body-sm);line-height:1.55}
.r-pros b,.r-cons b{color:var(--ink);font-weight:600;display:block;margin-bottom:4px;font-size:var(--t-cap);text-transform:uppercase;letter-spacing:0.4px}
.r-pros{color:var(--ink-muted)}
.r-cons{color:var(--ink-subtle)}
.r-meta{display:flex;flex-wrap:wrap;gap:6px;font-size:var(--t-cap);color:var(--ink-subtle);border-top:1px solid var(--hairline);padding-top:12px;margin-top:4px}
.skel{background:var(--s2);border-radius:var(--r-md);height:14px;margin:4px 0;animation:sh 1.2s ease-in-out infinite}
@keyframes sh{0%,100%{opacity:.55}50%{opacity:1}}
.empty{color:var(--ink-subtle);font-size:var(--t-body);text-align:center;padding:48px 16px;border:1px dashed var(--hairline);border-radius:var(--r-lg)}
footer{margin-top:96px;text-align:center;color:var(--ink-tertiary);font-size:var(--t-cap)}
.footer-link{color:var(--ink-subtle);text-decoration:none;border-bottom:1px solid var(--hairline)}
.examples{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ex{background:var(--s1);border:1px solid var(--hairline);color:var(--ink-muted);
  border-radius:var(--r-pill);padding:4px 12px;font-size:var(--t-cap);cursor:pointer;transition:all .15s}
.ex:hover{background:var(--s2);border-color:var(--hairline-strong);color:var(--ink)}
.kbd{font-family:ui-monospace,SF Mono,Menlo,monospace;font-size:var(--t-cap);
  background:var(--s2);border:1px solid var(--hairline);border-radius:var(--r-xs);
  padding:1px 6px;color:var(--ink-muted)}
"""

HTML = """<!doctype html>
<html lang="pt-br"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Model pick · LLM advisor</title>
<style>__CSS__</style>
</head><body>
<div class="wrap">
<p class="eyebrow">model pick</p>
<h1>qual llm pra esse trabalho?</h1>
<p class="sub">descreve o que vc quer fazer. a gente olha os 15 modelos mais usados hoje e recomenda os 3 melhores, com motivo, prós e contras e preço.</p>

<div class="card">
<div class="input-row">
<textarea id="task" placeholder="ex: transcrever e resumir reunião de 1h em português; gerar pipeline de dados em python com pandas; criar imagem de produto pra anúncio..." autofocus></textarea>
</div>
<div class="examples" style="margin-top:12px">
<span class="ex" data-q="resumir 50 artigos acadêmicos em português, gerar um sumário executivo">resumir 50 artigos</span>
<span class="ex" data-q="criar um site em react com tailwind, vai ter formulário, login, dashboard">criar site em react</span>
<span class="ex" data-q="transcrever áudio de reunião de 1h e gerar ata estruturada em pt-br">transcrever reunião 1h</span>
<span class="ex" data-q="gerar imagem de produto pra anúncio de e-commerce, várias variações">imagem pra anúncio</span>
<span class="ex" data-q="analisar código python de 10k linhas e achar bugs de performance">análise de código</span>
<span class="ex" data-q="responder perguntas em tempo real sobre um PDF de 800 páginas, citar trechos">perguntas sobre PDF grande</span>
</div>
<div class="input-row" style="margin-top:16px;align-items:center">
<button class="btn" id="go" onclick="recommend()">recomendar</button>
<span class="kbd" style="margin-left:8px">ctrl+enter</span>
<span id="status" style="margin-left:auto;color:var(--ink-subtle);font-size:var(--t-cap)"></span>
</div>
</div>

<div id="results" class="results"></div>

<div class="cta-banner" style="margin-top:48px">
<p class="eyebrow" style="margin:0 0 12px">como funciona</p>
<p style="margin:0 0 16px;color:var(--ink)">a gente olha 15 modelos (gpt, claude, gemini, llama, qwen, deepseek, mistral, grok) com notas por categoria (código, raciocínio, escrita, contexto longo, visão, áudio, multimodal) e pede pra um modelo de raciocínio forte (deepseek-r1) ranquear a sua tarefa específica, com preço como variável.</p>
<span class="chip">15 modelos · top 3 · prós e contras</span>
</div>
</div>
<footer>model pick · recomendação via openrouter · [REDACTED]</footer>

<script>
const $ = s => document.querySelector(s);
const results = $('#results');
const status = $('#status');

document.querySelectorAll('.ex').forEach(b => b.addEventListener('click', () => { $('#task').value = b.dataset.q; recommend(); }));
$('#task').addEventListener('keydown', e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') recommend(); });

function card(m, top){
  const meta = `${m.vendor} · ${m.ctx} ctx · $${m.out.toFixed(2)}/M out · $${m.in.toFixed(2)}/M in`;
  const pros = (m.pros || []).map(p => `<div>${p}</div>`).join('');
  const cons = (m.cons || []).map(c => `<div>${c}</div>`).join('');
  return `<div class="r-card ${top?'top':''}">${top?'<div class="badge-top">recomendado</div>':''}
    <div class="r-head"><div><p class="r-vendor">${m.vendor}</p><p class="r-title">${m.label}</p></div>
      <div class="r-score"><span class="r-score-num">${m.score.toFixed(1)}</span><span class="r-score-out">/10</span></div></div>
    <div class="r-pros"><b>por que</b>${pros}</div>
    <div class="r-cons"><b>cuidado</b>${cons}</div>
    <div class="r-meta">${meta} <a class="footer-link" style="margin-left:auto" href="https://openrouter.ai/models${m.id.replace('/','/')}" target="_blank" rel="noreferrer">ver no openrouter ↗</a></div>
  </div>`;
}

function skel(){
  return [0,1,2].map(() => `<div class="r-card"><div class="skel" style="width:60%"></div><div class="skel" style="width:90%"></div><div class="skel" style="width:80%"></div><div class="skel" style="width:70%"></div></div>`).join('');
}

async function recommend(){
  const q = $('#task').value.trim();
  if (!q) { $('#task').focus(); return; }
  results.innerHTML = skel();
  status.textContent = 'analisando...';
  $('#go').disabled = true;
  try {
    const r = await fetch('/api', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ task: q }) });
    const j = await r.json();
    if (j.error) throw new Error(j.error);
    results.innerHTML = j.picks.map((m,i) => card(m, i===0)).join('');
    status.textContent = `${j.picks.length} modelos selecionados · cache: ${j.cached ? 'sim' : 'não'}`;
  } catch (e) {
    results.innerHTML = `<div class="empty">erro: ${e.message}</div>`;
    status.textContent = '';
  } finally { $('#go').disabled = false; }
}
</script>
</body></html>"""


def cache_get(key):
    try:
        with open(CACHE_PATH) as f: d = json.load(f)
        e = d.get(key)
        if e and e["ts"] > time.time() - 86400: return e["value"]
    except Exception: pass
    return None

def cache_put(key, value):
    try:
        d = {}
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH) as f: d = json.load(f)
            except Exception: d = {}
        d[key] = {"ts": time.time(), "value": value}
        if len(d) > 200: d = dict(list(d.items())[-200:])
        with open(CACHE_PATH, "w") as f: json.dump(d, f)
    except Exception: pass


SYSTEM = """Voce e um advisor de LLMs. O usuario descreve uma tarefa. Voce recebe:
1. uma lista de modelos com notas (1-10) por categoria e preco
2. a tarefa do usuario

Escolha os 3 melhores modelos pra essa tarefa. Justifique cada um com 2-3 PROS (por que serve) e 2 CONS (cuidado/limitacao) curtos (uma frase cada). Use o preco como variavel (se o user nao citou orcamento, prefira custo-beneficio).

Responda APENAS em JSON valido com este schema, sem markdown, sem texto antes/depois:
{"picks":[{"id":"<model_id>","score":<1-10 com 1 casa>,"pros":["..."],"cons":["..."]}]}
A ordem dos picks deve ser do melhor (indice 0) pro pior. Score 10 so se for claramente o melhor da categoria."""


def call_openrouter(task):
    catalog_lines = []
    for m in MODELS:
        s = m["scores"]
        catalog_lines.append(f'- {m["id"]} | {m["label"]} ({m["vendor"]}, ctx {m["ctx"]}, ${m["out"]}/M out, ${m["in"]}/M in) | code:{s["code"]} reason:{s["reason"]} write:{s["write"]} long:{s["long"]} vision:{s["vision"]} audio:{s["audio"]} multi:{s["multi"]} price_eff:{s["price_eff"]}')
    catalog = "\n".join(catalog_lines)
    user_msg = f"TAREFA DO USUARIO: {task}\n\nCATALOGO DE MODELOS:\n{catalog}\n\nResponda em JSON valido, schema {{'picks':[{{'id','score','pros','cons'}}]}}."
    body = {
        "model": "deepseek/deepseek-chat-v3",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    msg = data.get("choices", [{}])[0].get("message", {}) or {}
    txt = (msg.get("content") or msg.get("reasoning") or "").strip()
    if not txt:
        raise ValueError(f"resposta vazia do advisor (finish={data.get('choices',[{}])[0].get('finish_reason')})")
    if txt.startswith("```"):
        txt = txt.split("\n", 1)[1]
        if txt.endswith("```"): txt = txt[:-3]
    j = json.loads(txt)
    return j["picks"]


def enrich(picks):
    by_id = {m["id"]: m for m in MODELS}
    out = []
    for p in picks:
        m = by_id.get(p["id"])
        if not m: continue
        out.append({
            "id": m["id"], "label": m["label"], "vendor": m["vendor"],
            "ctx": m["ctx"], "out": m["out"], "in": m["in"],
            "score": float(p.get("score", 7)),
            "pros": p.get("pros", [])[:3], "cons": p.get("cons", [])[:3],
        })
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass  # silencia log

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.replace("__CSS__", CSS).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", "0"))
        try:
            raw = self.rfile.read(n) or b"{}"
            try: req = json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError: req = json.loads(raw.decode("latin-1"))
            task = (req.get("task") or "").strip()
            if not task:
                self._json({"error": "tarefa vazia"}, 400); return
            key = hashlib.sha256(task.lower().encode()).hexdigest()
            cached = cache_get(key)
            if cached:
                self._json({"picks": cached, "cached": True}); return
            picks = call_openrouter(task)
            picks = enrich(picks)
            if not picks:
                self._json({"error": "modelo advisor nao retornou picks validos"}, 502); return
            cache_put(key, picks)
            self._json({"picks": picks, "cached": False})
        except urllib.error.HTTPError as e:
            try: body = e.read().decode("utf-8", errors="replace")[:300]
            except Exception: body = "<unreadable>"
            self._json({"error": f"openrouter {e.code}: {body}"}, 502)
        except UnicodeDecodeError as e:
            import traceback; self._json({"error": f"decode {e.start}-{e.end}: {e.object[:80]!r}"}, 500)
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _json(self, obj, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    print(f"model pick on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

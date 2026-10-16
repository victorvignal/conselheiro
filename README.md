# conselheiro

Site que recomenda o LLM ideal pro trabalho que a pessoa quer fazer. Descreve a tarefa em texto livre, o site analisa 15 modelos (GPT, Claude, Gemini, Llama, Qwen, DeepSeek, Mistral, Grok) e devolve o top 3 com score, prós, contras e preço.

## como rodar

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
python server.py            # sobe em http://127.0.0.1:8765
```

## como funciona

1. usuário descreve a tarefa (ex: "resumir 50 artigos em português")
2. backend monta um catálogo dos 15 modelos com notas por categoria (código, raciocínio, escrita, contexto longo, visão, áudio, multimodal, custo-benefício) e preço
3. pede pro DeepSeek V3 ranquear e justificar em JSON
4. front renderiza top 3 com "por que" e "cuidado"
5. cache de 24h por tarefa (hash do texto) pra não estourar cota

## stack

- backend: Python stdlib puro (http.server + urllib), sem dependências
- advisor: DeepSeek V3 via OpenRouter
- front: HTML+CSS+JS inline, design system Linear (dark #010102, accent #5e6ad2)

## arquivo

- `server.py` — tudo em 1 arquivo (server + catalogo + html/css/js)

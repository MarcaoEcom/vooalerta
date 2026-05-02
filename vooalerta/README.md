# ✈️ VooAlerta

Bot que monitora voos com desconto no Google Flights e exibe num painel web.
Sem chaves de API, sem cartão de crédito. 100% gratuito.

---

## Como subir (passo a passo)

### 1. Suba os arquivos no GitHub

1. Acesse https://github.com/new
2. Nome do repositório: `vooalerta`
3. Deixe **privado** e clique em "Create repository"
4. Clique em "uploading an existing file"
5. Arraste todos os arquivos deste zip e clique em "Commit changes"

---

### 2. Suba no Railway

1. Acesse https://railway.app
2. Clique em **"Start a New Project"**
3. Escolha **"Deploy from GitHub repo"**
4. Autorize o Railway a acessar seu GitHub e selecione `vooalerta`
5. Clique no projeto criado → vá em **"Variables"** e adicione:

```
MINIMUM_DISCOUNT_PCT = 20
DAYS_AHEAD           = 30
SEARCH_HOUR          = 8
SEARCH_MINUTE        = 0
```

6. Vá em **"Settings"** → **"Networking"** → **"Generate Domain"**
7. Acesse o link gerado — seu painel está no ar! ✅

---

## Personalizar rotas

Edite o array `ROUTES` em `backend/main.py`:

```python
ROUTES = [
    {"origin": "POA", "destination": "GRU", "origin_city": "Porto Alegre", "dest_city": "São Paulo"},
    # adicione ou remova rotas aqui
]
```

Códigos IATA: https://www.iata.org/en/publications/directories/code-search/

---

## Estrutura

```
vooalerta/
├── backend/
│   ├── main.py      # bot de busca (Google Flights)
│   └── api.py       # servidor do painel web
├── frontend/
│   └── index.html   # painel visual
├── requirements.txt
├── railway.toml
└── .env.example
```

---

## Como funciona

```
Todo dia às 08h (configurável)
    ↓
Busca voos no Google Flights (sem API key)
    ↓
Filtra os com desconto acima do mínimo
    ↓
Salva no cache e exibe no painel
    ↓
[em breve] Dispara mensagem no WhatsApp
```

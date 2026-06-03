# Minha Vida — Rastreador Pessoal de Hábitos

Sistema de autorastreamento diário de hábitos e métricas pessoais. A entrada de dados acontece via **WhatsApp** e a análise via **dashboard Streamlit**.

---

## Arquitetura

```
WhatsApp Cloud API
       ↓ webhook POST
Backend FastAPI  (backend/whats.py)
       ↕ SQLAlchemy ORM
PostgreSQL Neon  (produção)
       ↑ SQL SELECT
Frontend Streamlit  (frontend/Habitos.py)
```

---

## Estrutura do projeto

```
Minha_vida/
├── backend/
│   ├── whats.py              # FastAPI + webhook WhatsApp
│   ├── models.py             # SQLAlchemy ORM — tabela minha_vida
│   ├── dependencies.py       # Context manager pegar_sessao()
│   └── scripts/
│       ├── importar_dados.py # Importa histórico via Excel
│       └── limpar_banco.py   # Apaga todos os registros (com confirmação)
├── frontend/
│   ├── Habitos.py            # Dashboard principal
│   ├── foto_diogo.jpg
│   ├── pages/
│   │   ├── Humor.py          # Análise de humor
│   │   └── Sono.py           # Análise de sono
│   └── utils/
│       ├── graficos.py       # Funções de gráfico ECharts e Plotly
│       ├── tratamente_dados.py  # preparar_df(): limpeza e transformações
│       └── transformadores.py   # Agregações para alimentar os gráficos
├── alembic/                  # Migrações do banco
├── Procfile                  # uvicorn backend.whats:app
├── build.sh                  # pip install + alembic upgrade head
└── requirements.txt
```

---

## Hábitos rastreados

| Categoria | Hábitos |
|---|---|
| Saúde do corpo | Academia, Exercício aeróbico, Alimentação saudável, Consumo de água |
| Evolução pessoal | Estudar, Leitura |
| Lazer | Atividade sexual, Secreto |

**Métricas:** nota de humor (início e fim do dia), hora que acordou, hora que foi dormir.

---

## Deploy

| Serviço | Plataforma | Branch |
|---|---|---|
| Backend (WhatsApp bot) | Render | `master` |
| Frontend (dashboard) | Streamlit Community Cloud | `master` |

**Variáveis de ambiente necessárias:**

```
DATABASE_URL=postgresql://...
API_VERSION=v18.0
PHONE_NUMBER_ID=...
ACCESS_TOKEN=...
VERIFY_TOKEN=...
```

---

## Rodar localmente

```bash
# Backend
uvicorn backend.whats:app --host 0.0.0.0 --port 8000

# Frontend
streamlit run frontend/Habitos.py
```

---

## Dashboard

- **Métricas** — aderência total e por hipercategoria com delta semanal
- **Liquid fill** — percentual de aderência geral
- **Drilldown** — aderência por hipercategoria → hábito
- **Barras empilhadas** — aderência por dia da semana, semana do mês e mês/ano
- **Mapa de correlação** — Pearson entre hábitos (resample semanal)
- **Calendário heatmap** — atividades por dia, anos detectados automaticamente

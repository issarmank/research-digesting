# Research Digest

An autonomous research pipeline that searches the web, filters noise, synthesizes insights, and emails a structured digest — all triggered from a local Streamlit UI.

## What it does

1. **Scout** — queries Tavily for recent articles on each configured topic
2. **Curator** — deduplicates against a SQLite store so you never see the same article twice
3. **Writer** — scores each article for relevance (0–1), drops low-signal content, and synthesizes keepers into a structured digest with an overview, key insights, and themed sections
4. **Dispatcher** — renders an HTML email via Jinja2 and sends it through Resend

The UI lets you manage topics, set an email recipient, trigger runs on demand, watch live log output, and browse digest history — no terminal required.

## Stack

| Layer | Tech |
|---|---|
| Agents / orchestration | CrewAI |
| LLM | Groq (llama-3.3-70b-versatile via litellm) |
| Search | Tavily Python SDK |
| Email | Resend + Jinja2 |
| Persistence | SQLite |
| Frontend | Streamlit |
| Output schema | Pydantic |

## Project layout

```
backend/
  agents/
    scout.py        # Tavily search + result formatting
    curator.py      # SQLite dedup + digest persistence
    writer.py       # Relevance scoring + digest synthesis (Pydantic output)
    dispatcher.py   # Resend email delivery
  tasks/
    tasks.py        # CrewAI Task definitions
  templates/
    digest_email.html  # Jinja2 HTML email template
  memory/
    seen_urls.db    # SQLite: seen_urls + digests tables
  crew.py           # Main pipeline: run(topics?) -> list[Digest]
  config.py         # TOPICS, GROQ_MODEL, env loading
  scheduler.py      # (retired) APScheduler-based cron runner
frontend/
  app.py            # Streamlit UI
  settings.json     # Persisted topics + email recipient
```

## Setup

### 1. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure environment

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
RESEND_API_KEY=your_resend_key
TO_EMAIL=you@example.com
```

### 3. Run the UI

```bash
streamlit run frontend/app.py
```

Open [localhost:8501](http://localhost:8501).

### 4. (Optional) Run from the CLI

```bash
cd backend
python crew.py
```

## UI walkthrough

**Sidebar** — edit topics (one per line), set email recipient, click Save.

**Run Now** — triggers the full pipeline in a background thread. The button disables while the run is in progress.

**Live log** — log lines stream in real time as Scout, Curator, Writer, and Dispatcher execute. Expands automatically during a run.

**Digest preview** — renders the current session's output: overview, key insights, themed synthesis sections, and sources.

**History** — reads past digests from SQLite. Survives restarts. Expandable detail view per run.

## How the pipeline works

```
search_topic(topic)          # Tavily → raw text blocks
  └─> Scout agent            # formats into numbered list
      └─> deduplicate()      # SQLite filter — drops seen URLs
          └─> Writer agent   # scores relevance, synthesizes digest
              └─> save_digest()          # persists to SQLite
              └─> send_digest_email()    # Resend → inbox
```

Rate limits: 60s pause between topics, 30s between Scout and Writer calls (Groq TPM).

## Digest schema (Pydantic)

```python
class Digest(BaseModel):
    topic: str
    overview: str                        # 3-sentence executive summary
    key_insights: list[str]              # 3-5 non-obvious takeaways
    sections: list[DigestSection]        # themed synthesis (heading + body)
    scored_articles: list[ArticleScore]  # relevance score per article
    sources: list[str]                   # URLs of kept articles
    total_articles: int
    included_articles: int
```

Articles with `relevance_score >= 0.6` are kept; the rest are logged as dropped with a reason.

## Customising topics

Edit topics in the Streamlit sidebar and click Save — changes persist to `frontend/settings.json` and take effect on the next run. Alternatively, edit `backend/config.py` directly for CLI runs.

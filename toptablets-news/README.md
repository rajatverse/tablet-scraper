# TopTablets.in AI Tablet News Automation System

An autonomous news discovery, verification, editorial drafting, and publishing pipeline for [TopTablets.in](https://toptablets.in).

## Architecture & Lifecycle

```
[RSS Feeds / Google News]
           │
           ▼
   fetch_rss.py             ──> Discovers raw stories (State: 'discovered')
           │
           ▼
filter_tablet_news.py       ──> Rejects non-tablet & non-India noise ('qualified' or 'rejected')
           │
           ▼
    deduplicate.py          ──> Clusters identical multi-publisher stories into Topics ('research_pending' / 'duplicate_grouped')
           │
           ▼
   research_story.py        ──> Extracts body text via Trafilatura & constructs fact sheets ('verified')
           │
           ▼
  generate_article.py       ──> Synthesizes SEO-optimized HTML article & metadata ('drafted')
           │
           ▼
  validate_article.py       ──> Quality auditor checks fields, constraints & prices ('quality_passed' / 'quality_failed')
           │
           ▼
 publish_wordpress.py       ──> Creates idempotent draft posts via REST API ('published')
```

## Directory Structure

```
toptablets-news/
├── config/
│   ├── settings.yaml            # Scoring thresholds, site URLs, category IDs
│   ├── sources.json             # RSS feed definitions (Google News, Indian tech media)
│   ├── tablet_keywords.json     # Brand names, series, form factors & exclusion rules
│   └── editorial_rules.yaml     # Word counts, fact rules, quality criteria
├── data/
│   ├── news.db                  # SQLite database tracking story states and topics
│   ├── logs/                    # pipeline.log
│   └── cache/
├── scripts/
│   ├── db.py                    # SQLite database access & state transitions
│   ├── fetch_rss.py             # RSS feed discovery
│   ├── filter_tablet_news.py    # Rule-based filtering & categorization
│   ├── deduplicate.py           # Multi-source story clustering & topic grouping
│   ├── research_story.py        # Deep Trafilatura extraction & fact sheets
│   ├── llm_client.py            # Local Ollama client with built-in synthesizer fallback
│   ├── generate_article.py      # Article synthesis & SEO metadata generation
│   ├── validate_article.py      # Anti-hallucination & quality audit
│   └── publish_wordpress.py     # WordPress REST API draft publisher
├── prompts/
│   └── write_news.txt           # Structured system prompt for news editor
├── main.py                      # Master CLI orchestrator
└── README.md
```

## CLI Usage

Run any stage individually or the entire pipeline autonomously:

```bash
# View current status of all stories in the pipeline
python toptablets-news/main.py status

# Run discovery across all feeds
python toptablets-news/main.py discover

# Filter for consumer tablet relevance
python toptablets-news/main.py filter

# Group identical announcements across publishers
python toptablets-news/main.py deduplicate

# Extract source text and build fact sheets
python toptablets-news/main.py research --limit 5

# Draft articles from verified research records
python toptablets-news/main.py draft --limit 3

# Run quality & fact-integrity audit
python toptablets-news/main.py validate

# Publish approved drafts to WordPress
python toptablets-news/main.py publish --limit 2

# Run full pipeline end-to-end
python toptablets-news/main.py run-all --limit 3
```

## Local LLM Setup (GTX 1650 4GB VRAM)

To enable local model generation:
1. Install Ollama: `winget install Ollama.Ollama`
2. Pull recommended compact model: `ollama run gemma2:2b` or `ollama run qwen2.5:3b`
3. If Ollama is offline or uninstalled, the pipeline automatically falls back to its deterministic, rule-verified editorial synthesizer.

# Frontier Atlas — AI Data Intelligence Pipeline

Frontier Atlas is an asynchronous data-ingestion and enrichment pipeline for collecting structured information from public AI ecosystem sources.

The project combines web/API scraping, structured validation, LLM orchestration, deterministic entity resolution, freshness checks, and spreadsheet-ready output.

## Project Goals

- Collect 1,000+ startup records.
- Collect 1,000+ AI product records.
- Collect 1,000+ research papers with GitHub metadata when available.
- Collect fresh AI jobs and news from the last 24 hours.
- Normalize entity names into canonical forms.
- Preserve source URLs for traceability.
- Validate datasets before export.
- Produce a six-tab spreadsheet for Google Sheets.

## Architecture

```text
Public Sources
     |
     +-------------------+
     |                   |
   APIs / RSS         Web Pages
     |                   |
     +---------+---------+
               |
        Async Scrapers
       aiohttp / Playwright
               |
        Structured Records
               |
     +---------+----------+
     |                    |
 Enrichment           LLM Layer
 GitHub             Gemini -> Groq
 metadata           -> DeepSeek
     |                    |
     +---------+----------+
               |
        Data Validation
       Pydantic + Quality
               |
        Entity Resolution
     Raw Name -> Canonical Name
               |
          JSON Storage
               |
       Spreadsheet Export
               |
     Frontier_Atlas.xlsx
               |
        Google Sheets
```

## Data Sources

The implemented pipeline uses public sources including:

- Y Combinator company directory — startup discovery
- ToolDirectory — AI product discovery
- arXiv — research papers
- GitHub — repository resolution and star enrichment
- Remotive, Remote OK, Jobicy, Himalayas and Arbeitnow — job discovery
- TechCrunch, VentureBeat, The Verge, WIRED and Ars Technica — AI news discovery

Source URLs are retained with collected records so data can be traced back to the originating source.

## Repository Structure

```text
frontier-atlas/
├── architecture.pdf
├── README.md
├── requirements.txt
├── test_llm.py
├── src/
│   ├── entity/
│   ├── llm/
│   ├── models/
│   ├── pipelines/
│   ├── scrapers/
│   ├── storage/
│   └── utils/
├── tests/
└── data/
    └── output/
```

## Main Components

### Scrapers

- `src/scrapers/base.py` — async HTTP client, concurrency limits and retries
- `src/scrapers/papers.py` — arXiv paper collection
- `src/scrapers/github.py` — GitHub repository resolution and stars
- `src/scrapers/startups.py` — YC startup collection
- `src/scrapers/products.py` — AI product collection
- `src/scrapers/jobs.py` — fresh AI job collection
- `src/scrapers/news.py` — fresh AI news collection

### Pipelines

Each dataset has a dedicated pipeline responsible for collection, validation, enrichment and persistence.

### LLM Orchestration

The LLM layer uses a provider abstraction and fallback chain:

```text
Gemini
   ↓ failure
Groq
   ↓ failure
DeepSeek
```

Rate-limit errors use retry/backoff logic. Large inputs are designed to be handled using chunking so oversized requests can be processed safely.

### Entity Resolution

Entity names are normalized deterministically using known mappings and normalization rules.

Example:

```text
OpenAI
Open AI
OpenAI Inc.
        ↓
      OpenAI
```

The raw-to-canonical relationship is stored in the Entity Mapping Log.

## Data Quality

The project includes an automated validation gate:

```bash
python src/utils/data_validator.py
```

The validator checks:

- Record counts
- Required fields
- Source URLs
- Duplicate records
- Date validity
- 24-hour freshness for Jobs and News
- Entity mapping output

Latest validated dataset:

| Dataset | Records |
|---|---:|
| Startups | 1,000 |
| Products | 1,000 |
| Research Papers | 1,000 |
| Jobs | 17 |
| News | 5 |
| Entity Mapping Log | 1,000 |

Validation result:

```text
STATUS: PASS
ERRORS: 0
WARNINGS: 0
```

## Spreadsheet Output

The pipeline creates:

```text
data/output/Frontier_Atlas.xlsx
```

The workbook contains six tabs:

1. Startups
2. Products
3. Research Papers
4. Jobs
5. News
6. Entity Mapping Log

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file for API credentials. Never commit `.env` or API keys to GitHub.

Example:

```env
GEMINI_API_KEY=
GROQ_API_KEY=
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
```

## Running Tests

Run the complete test suite:

```bash
pytest -q
```

Expected result for the current test suite:

```text
10 passed
```

## Running Pipelines

Examples:

```bash
python src/pipelines/startup_pipeline.py
python src/pipelines/product_pipeline.py
python src/pipelines/research_pipeline.py
python src/pipelines/job_pipeline.py
python src/pipelines/news_pipeline.py
python src/pipelines/entity_mapping_pipeline.py
```

Spreadsheet export:

```bash
python src/storage/spreadsheet_export.py
```

## Reliability

The pipeline is designed to continue operating when individual external services fail.

Key mechanisms include:

- Async requests with bounded concurrency
- Exponential retry with jitter
- HTTP 429 rate-limit handling
- HTTP 413-aware LLM chunking
- Per-source failure isolation
- Deduplication
- Freshness validation
- Source traceability
- Structured schema validation

GitHub enrichment may be skipped when the public GitHub API quota is exhausted; the underlying research-paper record remains valid.

## Scalability

The current implementation is organized so the local JSON storage layer can evolve toward a distributed architecture.

For approximately 500k+ records, the reference design is:

```text
Sources
   ↓
Message Queue
   ↓
Distributed Async Workers
   ↓
Raw Object Storage
   ↓
Validation / Enrichment
   ↓
Entity Resolution
   ↓
Relational DB + Vector / Graph Stores
   ↓
Analytics / Export
```

Important scale principles:

- Partition ingestion by source and time window.
- Use queues to isolate failures and absorb bursts.
- Retain raw payloads for auditability and replay.
- Use stable source/entity keys for idempotent processing.
- Prefer incremental updates over full rebuilds.
- Track freshness and provenance as first-class metadata.

## Security

- API credentials are loaded from environment variables.
- `.env` is excluded from version control.
- Secrets should never be placed in source files or committed to GitHub.
- Logs should not expose API credentials.

## Engineering Artifacts

The repository includes:

- Source code under `src/`
- Automated tests under `tests/`
- `README.md`
- `architecture.pdf`
- Structured JSON output
- `Frontier_Atlas.xlsx`

## License

This project is an assignment/project implementation for Frontier Atlas.

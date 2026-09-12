# Frontier Atlas — AI Data Intelligence Pipeline

Frontier Atlas is an asynchronous data-ingestion and enrichment pipeline designed to collect structured information from public AI ecosystem sources.

The system combines web scraping, API ingestion, validation, LLM orchestration, deterministic entity resolution, deduplication, and spreadsheet export.

---

## 1. Project Overview

Frontier Atlas collects and structures information across the AI ecosystem into six datasets:

- Startups
- Products
- Research Papers
- Jobs
- News
- Entity Mapping Log

The pipeline is designed with a focus on:

- Reliable source traceability
- Structured data validation
- Asynchronous collection
- Rate-limit handling
- LLM fallback orchestration
- Deterministic entity resolution
- Duplicate detection
- Freshness validation
- Spreadsheet-ready output
---
## 2. Architecture
```text
                    ┌──────────────────────┐
                    │   Public Data Sources │
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       API / RSS Sources                  Web Sources
              │                                 │
              └────────────────┬────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Async Scraper Layer │
                    │  aiohttp / Playwright│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Raw Structured Data  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ LLM Orchestration    │
                    │ Gemini → Groq →      │
                    │ DeepSeek             │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Data Validation      │
                    │ Pydantic + Quality   │
                    │ Checks                │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Entity Resolution    │
                    │ Raw → Canonical      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ JSON Storage         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Excel / Google Sheet │
                    │ 6 Data Tabs          │
                    └──────────────────────┘
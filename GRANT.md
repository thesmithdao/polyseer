# Polyseer — The Polymarket Oracle MCP Server & uAgent

**Funding Ask:** 1,500 USD
**Milestones:** 1
**Domain:** Infrastructure & Tooling

---

## tl;dr

A reusable Polymarket oracle — a uAgent **and** MCP server that gives any AI agent
natural-language access to live prediction-market odds, calibrated forecasts,
trending markets, and market discovery.

## What I'm Building

Polyseer makes **prediction-market intelligence** usable by AI agents and people
through one simple interface. Instead of scraping Polymarket's APIs or parsing
order books, anyone — a human in ASI:One, or another autonomous agent — can ask:

> *"What are the odds the Fed cuts rates in July?"*
> *"What's the implied probability on the BTC $100k market?"*
> *"What are the hottest prediction markets right now?"*

…and get a structured, sourced answer: a calibrated probability, the live
market-implied odds, links back to the underlying Polymarket markets, and a short
transparent rationale.

The agent is delivered two ways from one codebase:

1. **uAgent on Agentverse** — discoverable in the marketplace and routable from
   **ASI:One** via the Agent Chat Protocol.
2. **MCP server** — the same capabilities exposed as MCP tools
   (`forecast`, `market_odds`, `trending_markets`, `search_markets`), so any
   MCP-compatible AI system can use Polymarket intelligence as easily as it uses
   weather or stock data.

This grant does **not** fund research. The agent already exists as an open-source
MVP (uAgent + intent router + live Polymarket Gamma integration + configurable LLM
backend). The goal is to **package it as a discoverable, interoperable building
block** for the agent ecosystem: ship the MCP server, deploy it, register it on
Agentverse, and document it for other developers and agents to compose with.

## Why It Matters

Prediction markets are one of the best real-time, money-weighted signals of what
will happen — yet that signal is locked behind raw APIs, double-encoded JSON, and
order-book mechanics that most builders and **almost no AI agents** can use
programmatically.

There is currently **no clean, reusable prediction-market intelligence service in
the agent ecosystem.** Polyseer changes that: it turns Polymarket into a standard,
composable capability that supports forecasting, research, trading-adjacent
analytics, news/markets cross-checking, and any agent that benefits from "what's
the probability of X?"

My goal is simple: make credible, calibrated probability estimates as accessible
and reusable as any other piece of digital infrastructure.

## Roadmap

**Week 1**
- Wrap the existing Polymarket capabilities as an **MCP server** (`forecast`,
  `market_odds`, `trending_markets`, `search_markets`) with a structured
  request/response schema and source attribution.
- Deploy the uAgent on Railway (public endpoint) and register it on Agentverse.

**Week 2**
- Enable discovery through **ASI:One** (keyword-rich profile, tags, manifest).
- Add input validation, error handling, response caching (Polymarket rate limits),
  and a live-price tool via the Polymarket CLOB API.
- Ship an **agent-to-agent integration example** (one agent calling Polyseer).

**Week 3**
- Publish documentation and a public demo of real prediction-market queries.
- Prototype an **x402-gated premium tool** (pay-per-call in stablecoin) to fit the
  machine-payable agent economy.
- Open-source release polish.

**Expected completion:** within three weeks of approval.

## Credibility / Delivery Risk

Delivery risk is **low** — the core is already built and open-source:

- Working uAgent with the Agent Chat Protocol (ASI:One-compatible).
- Lean keyword **intent router**: forecast, market lookup, trending, discovery.
- Live **Polymarket Gamma** integration with defensive parsing of Polymarket's
  double-encoded fields.
- **Configurable LLM** backend (ASI:One by default; Claude / OpenAI optional).
- Railway + Agentverse deployment paths (mailbox and public-endpoint) documented.

The work funded here is packaging and distribution — MCP server, deployment,
discovery, docs, and the x402 prototype — not unproven research. It uses only
**public, read-only** Polymarket APIs (no trading, no custody).

## Links

- GitHub: `<your-repo-url>`
- Live demo / Agentverse profile: `<added on deploy>`
- Demo video: `<added in week 3>`

## Member Details

1. `<your name / role>` — `<one-line bio: independent builder working on agent
   infrastructure and prediction-market tooling>`

**GitHub:** `<your-github-handle>`

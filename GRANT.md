# Polyseer — The Polymarket Oracle Agent

**Funding Ask:** 1,500 USD
**Milestones:** 1
**Domain:** Infrastructure & Tooling

---

## tl;dr

A reusable Polymarket oracle — a uAgent on Agentverse that gives any ASI:One user
or autonomous agent natural-language access to live prediction-market odds,
calibrated forecasts, trending markets, and market discovery.

## What I'm Building

Polyseer makes **prediction-market intelligence** usable through one simple
interface. Instead of scraping Polymarket's APIs or parsing order books, anyone —
a human in ASI:One, or another autonomous agent — can ask:

> *"What are the odds the Fed cuts rates in July?"*
> *"What's the implied probability on the BTC $100k market?"*
> *"What are the hottest prediction markets right now?"*

…and get a structured, sourced answer: a calibrated probability, the live
market-implied odds, links back to the underlying Polymarket markets, and a short
transparent rationale.

It's delivered as a **uAgent on Agentverse**, discoverable in the marketplace and
routable from **ASI:One** via the Agent Chat Protocol — so it works both as a
chat interface for people and as a callable capability for other agents.

This grant does **not** fund research. The agent already exists as an open-source
MVP (uAgent + intent router + live Polymarket Gamma integration + configurable LLM
backend). The goal is to **harden it and make it the go-to prediction-market agent**
in the ecosystem: deploy it, register it on Agentverse, make it discoverable on
ASI:One, and document it for other developers and agents to compose with.

## Why It Matters

Prediction markets are one of the best real-time, money-weighted signals of what
will happen — yet that signal is locked behind raw APIs, double-encoded JSON, and
order-book mechanics that most builders and **almost no AI agents** can use
programmatically.

There is currently **no clean, reusable prediction-market intelligence agent in the
ecosystem.** Polyseer changes that: it turns Polymarket into a composable capability
that supports forecasting, research, market discovery, and any agent that benefits
from "what's the probability of X?"

My goal is simple: make credible, calibrated probability estimates as accessible and
reusable as any other piece of digital infrastructure.

## Roadmap

**Week 1**
- Deploy the uAgent on Railway (public endpoint) and register it on Agentverse.
- Finalize the structured response schema (probability + market odds + sources).

**Week 2**
- Enable discovery through **ASI:One** (keyword-rich profile, tags, manifest).
- Add input validation, error handling, and response caching (Polymarket rate limits).
- Add a live-price capability via the Polymarket CLOB API.

**Week 3**
- Publish documentation and a public demo of real prediction-market queries.
- Ship an **agent-to-agent integration example** (one agent calling Polyseer).
- Open-source release polish; drive the first real interactions for marketplace ranking.

**Expected completion:** within three weeks of approval.

## Credibility / Delivery Risk

Delivery risk is **low** — the core is already built and open-source:

- Working uAgent with the Agent Chat Protocol (ASI:One-compatible).
- Lean keyword **intent router**: forecast, market lookup, trending, discovery.
- Live **Polymarket Gamma** integration with defensive parsing of Polymarket's
  double-encoded fields.
- **Configurable LLM** backend (ASI:One by default; Claude / OpenAI optional).
- Railway + Agentverse deployment paths (mailbox and public-endpoint) documented.

The work funded here is hardening and distribution — deployment, discovery, live
prices, docs, and a demo — not unproven research. It uses only **public, read-only**
Polymarket APIs (no trading, no custody, no funds handled).

## Links

- GitHub: https://github.com/thesmithdao/polyseer
- Live demo / Agentverse profile: `<added on deploy>`
- Demo video: `<added in week 3>`

## Member Details

1. `<your name / role>` — `<one-line bio: independent builder working on agent
   infrastructure and prediction-market tooling>`

**GitHub:** `<your-github-handle>`

---

*Possible future extension (not part of this grant): expose the same capabilities as
MCP tools so non-Agentverse AI hosts can call Polymarket intelligence directly.*

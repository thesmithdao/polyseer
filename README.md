# 🔮 Polyseer — the Polymarket oracle

**Ask anything about [Polymarket](https://polymarket.com) in plain language and get
a calibrated answer.** Polyseer is a natural-language oracle for prediction markets:
betting odds, implied probabilities, trending markets, market discovery, and
calibrated forecasts — anchored on live Polymarket data.

It speaks the **Agent Chat Protocol**, so it's usable directly from **ASI:One** and
discoverable in the **Agentverse marketplace**.

> Keywords: Polymarket, prediction markets, odds, implied probability, forecast,
> betting odds, market discovery, crypto prediction markets, calibrated probability.
> Informational analysis only — not financial advice.

---

## What you can ask

| You ask | Polyseer does |
|---|---|
| *"What are the odds the Fed cuts rates in July?"* | **Forecast** — one calibrated probability + reasoning |
| *"What's the price on the BTC $100k market?"* | **Market lookup** — implied probabilities for that market |
| *"What are the hottest markets right now?"* | **Trending** — top markets by 24h volume |
| *"Find markets about the 2026 election"* | **Discovery** — a list of matching markets |

```
You:    What are the odds the Fed cuts rates at the July meeting?
Polyseer: **Estimate: ~72%**
          - Polymarket "Fed decreases rates in July?" trades 71% Yes on $480k liquidity.
          - CPI has softened; the market has drifted up over two weeks.
          - Risk: a hot jobs report before the meeting pulls this down fast.

          **Markets referenced:**
          - [Fed decreases interest rates in July?](https://polymarket.com/event/...)
```

## How it works

```
ASI:One / marketplace ──Chat Protocol──▶ Polyseer (uAgent)
                                              │  keyword intent router
                            ┌─────────────────┼─────────────────┐
                            ▼                 ▼                 ▼
                       trending           discovery          forecast / lookup
                            └──── Polymarket Gamma API ────┘   + LLM synthesis
                                  (public, no auth)            (ASI:One / Claude / OpenAI)
```

| File | Responsibility |
|---|---|
| [polyseer/agent.py](polyseer/agent.py) | uAgent + Chat Protocol entrypoint |
| [polyseer/router.py](polyseer/router.py) | Keyword intent routing → answer |
| [polyseer/polymarket.py](polyseer/polymarket.py) | Public Polymarket Gamma client |
| [polyseer/llm.py](polyseer/llm.py) | Pluggable LLM backend |
| [hosted_agent.py](hosted_agent.py) | Single-file build for the **Agentverse-hosted** runtime |

## Configurable LLM

Set `LLM_PROVIDER` (see [.env.example](.env.example)):

| `LLM_PROVIDER` | Backend | Needs |
|---|---|---|
| `asi1` *(default)* | ASI:One | `ASI_ONE_API_KEY` |
| `anthropic` | Claude (`claude-opus-4-8`, adaptive thinking) | `ANTHROPIC_API_KEY` |
| `openai` | OpenAI / compatible | `OPENAI_API_KEY` |

---

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set AGENT_SEED + your LLM key
```

Test the logic without the agent layer (needs an LLM key + internet):

```bash
python -m polyseer.router "What are the odds the Fed cuts rates in July?"
python -m polyseer.router "trending markets?"
```

Run the agent:

```bash
python -m polyseer.agent
```

## Deploy on Railway

1. Push to GitHub → Railway **New Project → Deploy from GitHub repo**.
2. Set env vars from [.env.example](.env.example): a long random `AGENT_SEED` + your LLM key.
3. Deploy (runs `python -m polyseer.agent` via [Procfile](Procfile) / [railway.json](railway.json)).

Then connect it to Agentverse — pick **one**:

**A. Mailbox (default).** Do nothing extra; open the **inspector link** from the
logs once to pair. The Mailroom queues messages if it restarts.

**B. Public endpoint.** For the *"Add your agent details → Name + Endpoint URL"* flow:
Railway → **Settings → Networking → Generate Domain**, set
`AGENT_ENDPOINT=https://<your-app>.up.railway.app/submit`, redeploy, then paste the
**Name** (`Polyseer`) and that **Endpoint URL** into Agentverse. The uAgent serves
incoming messages at `/submit`.

## Get discovered (marketplace + ASI:One)

The agent's README and profile are what ASI:One indexes for routing. From the
[discovery setup guide](https://docs.agentverse.ai/documentation/agent-discovery/setup-guide):

- [x] **Chat Protocol published** (`publish_manifest=True`) → "Chat with Agent" / ASI:One badge.
- [ ] **@handle** `@polyseer` (≤20 chars) and **Name** `Polyseer` (≤30).
- [ ] **Avatar + keyword-rich About** (Polymarket, odds, prediction markets, forecast).
- [ ] **Tags:** `finance`, `prediction-markets`, `polymarket`, `forecasting`, `LLM`, `crypto`.
- [ ] **Active status** (keep it running) + **≥10 real interactions** (ranking threshold).

---

## Scope & non-goals

**Read-only.** No trading, no wallet, no custody. Anchors on live Polymarket Gamma
data and never fabricates markets or prices. Roadmap: live CLOB prices + resolution
detail (phase 2), then discovery/verification polish (phase 3).

## License

[MIT](LICENSE). Built on [Fetch.ai uAgents](https://innovationlab.fetch.ai/resources/docs/intro),
[ASI:One](https://asi1.ai), and the public
[Polymarket Gamma API](https://docs.polymarket.com/developers/gamma-markets-api/overview).

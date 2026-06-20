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
You:    What are the odds the Fed cuts rates in July?
Polyseer: ~72% — "Fed decreases rates in July?" is trading 71% Yes on $480k liquidity
          and has drifted up over two weeks as CPI softened. The main thing that pulls
          it back down is a hot jobs report before the meeting.

You:    Will Bitcoin hit $100k by year end?
Polyseer: ~25% — BTC is at $63.7k right now, so $100k means a +57% move in six months,
          which the market prices at one-in-four. (live price: Binance, for context)
```

## How it works

```
ASI:One / marketplace ──Chat Protocol──▶ Polyseer (uAgent)
                                              │  LLM planner — dynamic intent + query
                            ┌─────────────────┼─────────────────┐
                            ▼                 ▼                 ▼
                       trending           discovery        forecast / ranked
                            └──── Polymarket Gamma API ────┘   + LLM synthesis
                                  (public, no auth)            (ASI:One / Claude / OpenAI)
                                                  ▲
            crypto questions: Binance public live spot ── supporting context only
```

| File | Responsibility |
|---|---|
| [polyseer/agent.py](polyseer/agent.py) | uAgent + Chat Protocol; per-user memory |
| [polyseer/router.py](polyseer/router.py) | Dispatch + answer synthesis |
| [polyseer/llm.py](polyseer/llm.py) | LLM planner (dynamic intent/query) + synthesis |
| [polyseer/polymarket.py](polyseer/polymarket.py) | Public Polymarket Gamma client |
| [polyseer/prices.py](polyseer/prices.py) | Binance public live crypto spot (context) |
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

## Deploy

Run it on any always-on host (a server, VM, or container platform):

1. Set the environment variables from [.env.example](.env.example): a long random
   `AGENT_SEED` and your LLM key (`ASI_ONE_API_KEY`).
2. Start it: `python -m polyseer.agent` (see [Procfile](Procfile)).
3. On first run, open the **inspector link** from the logs once, sign into
   Agentverse, and **Connect → Mailbox** to claim the agent under your account.

It connects **outbound** to Agentverse via the Mailbox, so it needs no public URL —
just keep the process running.

## License

[MIT](LICENSE). Built on [Fetch.ai uAgents](https://innovationlab.fetch.ai/resources/docs/intro),
[ASI:One](https://asi1.ai), and the public
[Polymarket Gamma API](https://docs.polymarket.com/developers/gamma-markets-api/overview).

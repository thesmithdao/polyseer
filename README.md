# 🔮 Oracle of Odds

**A calibrated-forecasting agent for the ASI / Agentverse ecosystem.**

Ask it any probabilistic question in plain language — *"What are the odds the Fed
cuts rates in July?"*, *"Will Bitcoin be above \$100k by year end?"*, *"Chance of
a recession in 2026?"* — and it returns a **single calibrated probability with
transparent reasoning**, anchored on live [Polymarket](https://polymarket.com)
prediction-market prices.

It speaks the **Chat Protocol**, so it's usable directly from **ASI:One** in
natural language, and it's discoverable on **Agentverse** via the Almanac.

> ℹ️ Informational analysis only — not financial advice.

---

## What it does

1. Receives a natural-language question over the Chat Protocol.
2. Searches the **public Polymarket Gamma API** (no key, no auth) for relevant
   markets and their crowd-sourced implied probabilities.
3. Hands those market priors to an LLM, which produces a **calibrated estimate +
   short reasoning + the markets it relied on.**

```
You:    What are the odds the Fed cuts rates at the July meeting?
Oracle: **Estimate: ~72%**
        - Polymarket "Fed decreases rates in July?" is trading at 71% Yes on $480k liquidity.
        - Recent CPI prints have softened; the market has been drifting up over two weeks.
        - Key risk: a hot jobs report before the meeting would pull this down fast.

        **Markets referenced:**
        - [Fed decreases interest rates in July?](https://polymarket.com/event/...)
```

## Architecture

```
ASI:One  ──Chat Protocol──▶  Oracle of Odds (uAgent, mailbox)
                                   │
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
          Polymarket Gamma API            LLM (configurable)
          (public, no auth)               ASI:One / Claude / OpenAI
```

| File | Responsibility |
|---|---|
| [oracle/agent.py](oracle/agent.py) | uAgent + Chat Protocol (ASI:One entrypoint) |
| [oracle/forecaster.py](oracle/forecaster.py) | Orchestration: question → markets → calibrated answer |
| [oracle/polymarket.py](oracle/polymarket.py) | Public Polymarket Gamma client (defensive parsing) |
| [oracle/llm.py](oracle/llm.py) | Pluggable LLM backend |

## Configurable LLM

Set `LLM_PROVIDER` (see [.env.example](.env.example)):

| `LLM_PROVIDER` | Backend | Needs |
|---|---|---|
| `asi1` *(default)* | ASI:One (Web3-native LLM) | `ASI_ONE_API_KEY` |
| `anthropic` | Claude via official SDK (`claude-opus-4-8`, adaptive thinking) | `ANTHROPIC_API_KEY` |
| `openai` | OpenAI / any OpenAI-compatible endpoint | `OPENAI_API_KEY` |

---

## Run locally

```bash
git clone <your-fork-url> oracle-of-odds && cd oracle-of-odds
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in AGENT_SEED + your LLM key
```

Smoke-test the forecasting pipeline without the agent layer (needs an LLM key
and outbound internet for Polymarket):

```bash
python -m oracle.forecaster "Will the Fed cut rates in July?"
```

Run the agent:

```bash
python -m oracle.agent
```

On startup you'll see:

```
INFO: [oracle-of-odds]: Registration on Almanac API successful
INFO: [oracle-of-odds]: Agent inspector available at https://agentverse.ai/inspect/?uri=...
INFO: [oracle-of-odds]: Starting server on http://0.0.0.0:8000
```

Open the **inspector link** once to connect the mailbox to your Agentverse
account (this pairs the agent so ASI:One can reach it).

## Deploy on Railway

1. Push this repo to GitHub.
2. On [Railway](https://railway.app): **New Project → Deploy from GitHub repo**.
3. Add environment variables from [.env.example](.env.example) — at minimum a
   long random `AGENT_SEED` and your selected LLM key. (Railway injects `PORT`.)
4. Deploy. Nixpacks installs `requirements.txt` and runs `python -m oracle.agent`
   (see [Procfile](Procfile) / [railway.json](railway.json)).
5. Open the inspector link from the deploy logs once to pair the mailbox.

The agent runs continuously and connects **outbound** to the Agentverse
Mailroom, so it doesn't need a public inbound URL — the Mailroom queues
messages if the process briefly restarts.

## Use it from ASI:One

Once the mailbox is paired and the manifest is published, ask ASI:One a
forecasting question (*"what are the odds …"*) and it can route to this agent.
The agent's description and example queries in this README are what ASI:One reads
to decide when Oracle of Odds is the right agent for a query.

---

## How forecasts are formed

- Polymarket prices are **money-weighted crowd forecasts** and serve as the
  prior the model anchors on.
- The model is instructed to flag when available markets don't exactly match the
  question, to express uncertainty, and never to fabricate markets or prices.
- Output is deliberately compact: one headline probability + a few bullets +
  source links.

## Limitations

- Quality depends on whether liquid Polymarket markets exist for the question.
- Polymarket's Gamma API double-encodes some fields as JSON strings; the client
  parses defensively, but upstream schema changes can still affect results.
- Informational only. No financial advice.

## License

[MIT](LICENSE).

## Acknowledgements

Built on [Fetch.ai uAgents](https://innovationlab.fetch.ai/resources/docs/intro)
+ the Chat Protocol, [ASI:One](https://asi1.ai), and the public
[Polymarket Gamma API](https://docs.polymarket.com/developers/gamma-markets-api/overview).

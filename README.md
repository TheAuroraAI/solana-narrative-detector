# Solana Narrative Detector

Automated detection of emerging narratives in the Solana ecosystem. Collects signals from on-chain program activity, GitHub developer trends, market data, and news feeds — then clusters them into scored narratives with concrete product ideas.

**Live Dashboard:** [https://solana-narrative-detector.onrender.com](https://solana-narrative-detector.onrender.com)

## What It Does

Every 2 hours, the detector runs a full collection cycle:

1. **On-chain signals** — Queries Solana mainnet RPC for transaction rates across 16 tracked programs (Jupiter, Orca, Raydium, Pump.fun, Drift, Tensor, etc.) plus new program deployments via the BPF Loader.

2. **GitHub signals** — Searches for newly created Solana repositories, monitors 15 ecosystem organizations (Solana Labs, Anza, Jito, Metaplex, Coral, etc.), and tracks commit activity on core repos (Agave, SPL, Anchor).

3. **Social/Market signals** — Pulls SOL price data, trending coins, developer stats, and community metrics from CoinGecko. Aggregates news from RSS feeds (Solana Blog, CoinDesk, Blockworks).

4. **Narrative analysis** — Maps collected signals against 12 narrative definitions using keyword matching, topic detection, and weighted scoring. Classifies each narrative's strength: very_strong, strong, moderate, emerging, or quiet.

5. **Idea generation** — Produces 3-5 concrete product ideas per detected narrative, each with a title and description explaining the opportunity.

## Narratives Tracked

| Narrative | Description |
|-----------|-------------|
| AI Agents & Autonomous Economy | AI agents operating on Solana — trading, deploying, transacting |
| DePIN | Decentralized physical infrastructure networks |
| Token-2022 & Extensions | Confidential transfers, transfer hooks, interest-bearing tokens |
| MEV & Priority Fees | Jito bundles, searcher activity, priority fee dynamics |
| ZK Compression | State compression via zero-knowledge proofs |
| Firedancer & Validator Diversity | Independent validator clients, performance improvements |
| Memecoin & Social Tokens | Pump.fun, bonding curves, community launches |
| Payments & Commerce | Solana Pay, Blinks/Actions, merchant adoption |
| Liquid Staking & Restaking | LSTs, Sanctum, validator economics |
| DeFi Innovation | Perps, prediction markets, CLMMs, on-chain orderbooks |
| Gaming & Entertainment | On-chain gaming, GameFi |
| Cross-Chain & Interoperability | Bridges, cross-chain messaging |

## Data Sources

- **Solana RPC** (mainnet-beta) — Program transaction signatures, performance samples, epoch info, supply data
- **GitHub API** — Repository search, organization repos, commit history
- **CoinGecko API** — SOL market data, trending coins, developer/community metrics
- **RSS Feeds** — Solana Blog, Solana Status, CoinDesk, Blockworks

## Signal Detection Methodology

Each narrative has a definition containing:
- **Keywords** — Terms that indicate relevance (e.g., "firedancer", "priority fee", "bonding curve")
- **GitHub topics** — Repository topics that correlate with the narrative
- **Program addresses** — On-chain programs directly related to the narrative
- **Weight** — Multiplier for narrative novelty (higher for emerging themes)

Scoring:
- On-chain: High activity (>100 tx/hr) = 3 points, moderate (>10 tx/hr) = 1.5 points
- GitHub: Trending repos (50+ stars) = 2 points, new repos (10+ stars) = 1 point
- News: Keyword match in RSS title = 1.5 points
- Market: Trending coin match = 2 points

Strength classification:
- **Very Strong** (10+) — Dominant narrative with many converging signals
- **Strong** (5-10) — Active narrative with solid signal presence
- **Moderate** (2-5) — Notable but not yet dominant
- **Emerging** (0.5-2) — Early signals worth watching
- **Quiet** (<0.5) — Minimal current activity

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Interactive dashboard |
| `/health` | GET | Health check |
| `/api/narratives` | GET | All narratives with scores and signals |
| `/api/narratives/{id}` | GET | Specific narrative details |
| `/api/ideas` | GET | All product ideas across narratives |
| `/api/history` | GET | Collection history over time |
| `/api/collect` | POST | Trigger manual collection cycle |

## Running Locally

```bash
pip install -r requirements.txt
python app.py
# Dashboard at http://localhost:8000
```

With GitHub token for higher API rate limits:
```bash
GITHUB_TOKEN=ghp_xxx python app.py
```

## Deployment

### Docker
```bash
docker build -t narrative-detector .
docker run -p 8000:8000 narrative-detector
```

### Render
The included `Dockerfile` is ready for deployment on Render. Set `PORT=8000` environment variable.

## Architecture

```
app.py                    # FastAPI application, scheduler, API routes
analyzer.py               # Narrative scoring engine, product idea generation
collectors/
  onchain.py              # Solana RPC data collection (16 programs, deployments, metrics)
  github.py               # GitHub API (trending repos, org activity, repo pulse)
  social.py               # CoinGecko market data, RSS feeds, keyword matching
templates/
  dashboard.html          # Interactive dashboard (dark theme, collapsible narratives)
data/                     # Persisted analysis results (JSON, auto-rotated)
```

## How to Reproduce

1. Clone this repository
2. `pip install -r requirements.txt`
3. `python app.py`
4. Open `http://localhost:8000` — the first collection cycle runs automatically on startup
5. Wait ~30 seconds for data collection to complete
6. Narratives, signals, and product ideas will appear on the dashboard

No API keys are required for basic operation. All data sources used are public APIs. Adding a `GITHUB_TOKEN` environment variable increases GitHub API rate limits from 10 to 30 requests per minute.

## License

MIT

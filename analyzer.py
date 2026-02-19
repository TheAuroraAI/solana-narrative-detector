"""
Narrative Detection Engine.
Clusters signals from on-chain, GitHub, and social sources into narratives.
Generates product ideas for each detected narrative.
"""

from datetime import datetime, timezone
from typing import Any
from collections import Counter


# Narrative definitions with signal patterns
NARRATIVE_DEFINITIONS = {
    "ai-agents": {
        "label": "AI Agents & Autonomous Economy",
        "description": "AI agents operating autonomously on Solana — trading, deploying programs, managing wallets, and transacting without human intervention.",
        "keywords": ["ai agent", "autonomous agent", "agent economy", "llm", "machine learning", "artificial intelligence", "autogpt", "langchain", "mcp"],
        "github_topics": ["ai", "agent", "llm", "machine-learning", "autonomous"],
        "programs": [],
        "weight": 1.2,  # Boost for high-novelty narratives
    },
    "depin": {
        "label": "DePIN (Decentralized Physical Infrastructure)",
        "description": "Physical infrastructure networks powered by Solana — wireless, sensors, compute, storage, mapping.",
        "keywords": ["depin", "helium", "hivemapper", "render", "io.net", "nosana", "physical infrastructure", "wireless", "iot"],
        "github_topics": ["depin", "iot", "infrastructure"],
        "programs": [],
        "weight": 1.1,
    },
    "token-extensions": {
        "label": "Token-2022 & Token Extensions",
        "description": "Advanced token features: confidential transfers, transfer hooks, permanent delegates, interest-bearing tokens.",
        "keywords": ["token-2022", "token extensions", "confidential transfer", "transfer hook", "permanent delegate", "interest-bearing", "token program"],
        "github_topics": ["token-2022", "token-extensions"],
        "programs": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],
        "weight": 1.0,
    },
    "mev-priority": {
        "label": "MEV & Priority Fee Markets",
        "description": "Maximum Extractable Value on Solana — Jito bundles, searcher activity, priority fee dynamics, sandwich attacks.",
        "keywords": ["mev", "jito", "priority fee", "sandwich", "bundle", "searcher", "tip", "backrun", "frontrun"],
        "github_topics": ["mev", "jito"],
        "programs": [],
        "weight": 1.0,
    },
    "zk-compression": {
        "label": "ZK Compression & State Compression",
        "description": "Compressing on-chain state using zero-knowledge proofs and Merkle trees — dramatically reducing costs.",
        "keywords": ["zk compression", "state compression", "compressed nft", "cnft", "light protocol", "merkle tree", "concurrent merkle"],
        "github_topics": ["zk", "compression", "zero-knowledge"],
        "programs": [],
        "weight": 1.1,
    },
    "firedancer": {
        "label": "Firedancer & Validator Diversity",
        "description": "Jump Crypto's independent Solana validator client — performance improvements, client diversity, network resilience.",
        "keywords": ["firedancer", "fire dancer", "frankendancer", "jump crypto", "validator client", "client diversity", "agave"],
        "github_topics": ["firedancer", "validator"],
        "programs": [],
        "weight": 1.0,
    },
    "memecoin-culture": {
        "label": "Memecoin & Social Token Culture",
        "description": "Pump.fun, bonding curves, community tokens, viral launches — Solana as the memecoin capital.",
        "keywords": ["pump.fun", "memecoin", "meme coin", "bonding curve", "fair launch", "community token", "degen"],
        "github_topics": ["memecoin", "pump"],
        "programs": ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"],
        "weight": 0.9,
    },
    "payments-commerce": {
        "label": "Payments & Commerce",
        "description": "Solana Pay, Blinks/Actions for in-context payments, merchant adoption, stablecoin transfers.",
        "keywords": ["solana pay", "payment", "blink", "actions", "commerce", "merchant", "stablecoin", "usdc", "usdt", "pyusd"],
        "github_topics": ["payments", "solana-pay", "blinks"],
        "programs": [],
        "weight": 1.0,
    },
    "liquid-staking": {
        "label": "Liquid Staking & Restaking",
        "description": "LSTs, Sanctum infinite LSTs, restaking protocols, validator economics.",
        "keywords": ["liquid staking", "lst", "sanctum", "marinade", "jito staking", "restaking", "msol", "jsol", "bsol", "inf"],
        "github_topics": ["staking", "liquid-staking", "lst"],
        "programs": ["MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD", "SWiMDJYFUGj6cPrQ6QYYYWZtvXQdRChSVAygDZDsCHC"],
        "weight": 1.0,
    },
    "defi-innovation": {
        "label": "DeFi Innovation",
        "description": "New DeFi primitives — perpetuals, prediction markets, CLMMs, intent-based trading, on-chain orderbooks.",
        "keywords": ["perpetual", "perps", "prediction market", "clmm", "intent", "orderbook", "amm", "drift", "phoenix", "openbook", "futarchy"],
        "github_topics": ["defi", "dex", "amm"],
        "programs": [
            "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
            "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
        ],
        "weight": 1.0,
    },
    "gaming-entertainment": {
        "label": "Gaming & Entertainment",
        "description": "On-chain gaming, GameFi, virtual worlds, entertainment apps on Solana.",
        "keywords": ["gaming", "gamefi", "game", "entertainment", "virtual world", "metaverse", "play-to-earn", "star atlas"],
        "github_topics": ["gaming", "gamefi"],
        "programs": [],
        "weight": 0.9,
    },
    "cross-chain": {
        "label": "Cross-Chain & Interoperability",
        "description": "Wormhole, bridges, cross-chain messaging, multi-chain applications.",
        "keywords": ["wormhole", "bridge", "cross-chain", "interop", "multi-chain", "layerzero", "allbridge"],
        "github_topics": ["bridge", "cross-chain", "interoperability"],
        "programs": [],
        "weight": 0.9,
    },
}


def score_narrative(
    narrative_id: str,
    definition: dict,
    onchain_data: dict,
    github_data: dict,
    social_data: dict,
) -> dict[str, Any]:
    """Score a narrative based on collected signals."""
    signals = []
    score = 0.0

    # 1. On-chain program activity signals
    program_activity = onchain_data.get("program_activity", [])
    for activity in program_activity:
        if activity.get("type") != "program_activity":
            continue
        addr = activity.get("address", "")
        if addr in definition.get("programs", []):
            tx_rate = activity.get("tx_per_hour_estimate", 0)
            if tx_rate > 100:
                signals.append(f"High on-chain activity: {activity['program']} ({tx_rate:.0f} tx/hr)")
                score += 3.0
            elif tx_rate > 10:
                signals.append(f"Active on-chain: {activity['program']} ({tx_rate:.0f} tx/hr)")
                score += 1.5

    # 2. GitHub signals
    trending = github_data.get("trending_repos", [])
    for repo in trending:
        topics = [t.lower() for t in repo.get("topics", [])]
        desc = (repo.get("description", "") or "").lower()
        name = repo.get("name", "").lower()

        # Check topic matches
        for topic in definition.get("github_topics", []):
            if topic in topics or topic in desc or topic in name:
                stars = repo.get("stars", 0)
                if stars >= 50:
                    signals.append(f"Trending repo: {repo['name']} ({stars}★) — {repo.get('description', '')[:80]}")
                    score += 2.0
                elif stars >= 10:
                    signals.append(f"New repo: {repo['name']} ({stars}★)")
                    score += 1.0
                else:
                    signals.append(f"Emerging repo: {repo['name']} ({stars}★)")
                    score += 0.5
                break

        # Check keyword matches in description
        for kw in definition.get("keywords", []):
            if kw.lower() in desc or kw.lower() in name:
                stars = repo.get("stars", 0)
                if stars >= 20:
                    signals.append(f"Related repo: {repo['name']} ({stars}★)")
                    score += 1.0
                break

    # 3. Org activity signals
    org_activity = github_data.get("org_activity", [])
    for activity in org_activity:
        desc = (activity.get("description", "") or "").lower()
        repo_name = activity.get("repo", "").lower()
        for kw in definition.get("keywords", []):
            if kw.lower() in desc or kw.lower() in repo_name:
                signals.append(f"Org activity: {activity['repo']}")
                score += 1.0
                break

    # 4. RSS/social signals
    rss_signals = social_data.get("rss_signals", [])
    for signal in rss_signals:
        if signal.get("error"):
            continue
        title = (signal.get("title", "") or "").lower()
        for kw in definition.get("keywords", []):
            if kw.lower() in title:
                signals.append(f"News: \"{signal['title'][:80]}\" ({signal.get('source', '')})")
                score += 1.5
                break

    # 5. Market signals (for ecosystem-level narratives)
    market = social_data.get("market_data", {})
    trending_coins = market.get("trending_coins", [])
    for coin in trending_coins:
        if coin.get("is_solana_ecosystem"):
            coin_name = coin.get("name", "").lower()
            for kw in definition.get("keywords", []):
                if kw.lower() in coin_name:
                    signals.append(f"Trending coin: {coin['name']} ({coin['symbol']})")
                    score += 2.0
                    break

    # Apply narrative weight
    score *= definition.get("weight", 1.0)

    return {
        "id": narrative_id,
        "label": definition["label"],
        "description": definition["description"],
        "score": round(score, 2),
        "signal_count": len(signals),
        "signals": signals[:15],  # Cap signals for readability
        "strength": _classify_strength(score),
    }


def _classify_strength(score: float) -> str:
    if score >= 10:
        return "very_strong"
    elif score >= 5:
        return "strong"
    elif score >= 2:
        return "moderate"
    elif score >= 0.5:
        return "emerging"
    else:
        return "quiet"


def generate_product_ideas(narrative: dict) -> list[dict[str, str]]:
    """Generate concrete product ideas for a detected narrative."""
    ideas_map = {
        "ai-agents": [
            {"title": "Agent Wallet Dashboard", "description": "Real-time dashboard showing autonomous AI agent wallet activity on Solana — transactions, PnL, strategies. Monetize via premium alerts."},
            {"title": "Agent-to-Agent Marketplace", "description": "On-chain protocol where AI agents can discover, negotiate, and pay each other for services using SPL tokens. Built on Solana for sub-second settlement."},
            {"title": "Agent Reputation Oracle", "description": "Soulbound reputation system for AI agents — track task completion rates, response quality, and reliability. Let agents build verifiable track records on-chain."},
            {"title": "Solana Agent SDK", "description": "TypeScript/Python SDK that makes it trivial for AI agents to interact with Solana: send tokens, deploy programs, read state, sign transactions. Reduce integration from days to hours."},
            {"title": "Agent Strategy Backtester", "description": "Replay historical Solana chain state to backtest autonomous agent strategies. Let builders validate their agents against real market conditions before deploying."},
        ],
        "depin": [
            {"title": "DePIN Analytics Dashboard", "description": "Unified analytics for all Solana DePIN protocols — Helium hotspot economics, Hivemapper coverage maps, io.net compute utilization. One dashboard to compare yields."},
            {"title": "DePIN Node Marketplace", "description": "Secondary market for DePIN hardware and node licenses on Solana. Let operators buy/sell Helium hotspots, Hivemapper dashcams with on-chain provenance."},
            {"title": "DePIN Yield Aggregator", "description": "Auto-compound DePIN rewards across protocols. Stake, claim, and reinvest HNT, HONEY, RENDER tokens in a single transaction using Jupiter routing."},
        ],
        "token-extensions": [
            {"title": "Token Extension Explorer", "description": "Block explorer specifically for Token-2022 assets. Show transfer hooks, confidential balances, interest accrual, and extension metadata in a user-friendly UI."},
            {"title": "Compliant Token Launchpad", "description": "Platform for launching tokens with built-in compliance via Token-2022 extensions — transfer restrictions, KYC hooks, and permanent delegate for clawback. Target institutional issuers."},
            {"title": "Privacy Token Wallet", "description": "Wallet optimized for confidential transfers on Solana. Encrypt balances, prove solvency without revealing amounts. Built on Token-2022 confidential transfers."},
        ],
        "mev-priority": [
            {"title": "MEV Dashboard", "description": "Real-time MEV activity monitor for Solana — sandwich attacks, arbitrage opportunities, Jito bundle analytics. Help traders understand and protect against MEV."},
            {"title": "Priority Fee Oracle", "description": "API service providing optimal priority fee estimates for Solana transactions. Use historical data and current mempool analysis. Charge per API call."},
            {"title": "MEV Protection Service", "description": "Transaction submission service that routes through Jito bundles with anti-sandwich protection. Simple API: submit tx, get MEV-protected confirmation."},
        ],
        "zk-compression": [
            {"title": "Compressed NFT Marketplace", "description": "Purpose-built marketplace for compressed NFTs (cNFTs). Handle the Merkle proof complexity invisibly. Let users mint collections of 1M+ NFTs for cents."},
            {"title": "ZK State Migration Tool", "description": "Tool that helps existing Solana programs migrate their account state to compressed representations. Reduce rent costs 1000x without changing program logic."},
            {"title": "Compressed Token Airdrop Platform", "description": "Mass airdrop platform using ZK compression. Send tokens to millions of wallets for a fraction of the cost. Target marketing teams and community managers."},
        ],
        "firedancer": [
            {"title": "Validator Performance Comparator", "description": "Compare Agave vs Firedancer validator performance in real-time — block production times, skip rates, transaction processing speeds. Help operators choose clients."},
            {"title": "Client Diversity Tracker", "description": "Dashboard tracking Solana's validator client diversity. Show Agave vs Firedancer adoption, geographic distribution, stake distribution. Critical for network health monitoring."},
            {"title": "Firedancer Migration Guide", "description": "Interactive guide and tooling for validators migrating from Agave to Firedancer. Automated config conversion, performance benchmarking, rollback procedures."},
        ],
        "memecoin-culture": [
            {"title": "Memecoin Sniper Bot", "description": "Real-time monitoring of Pump.fun launches with automated quality scoring. Detect rugs, track dev wallets, estimate market cap potential. Premium tier with auto-buy."},
            {"title": "Social Token Analytics", "description": "Track memecoin holder distribution, whale movements, and social sentiment across platforms. Identify early momentum before price moves."},
            {"title": "Community Token Launchpad", "description": "Fair-launch platform with anti-snipe mechanics, locked liquidity, and transparent bonding curves. Differentiate from Pump.fun with trust and safety features."},
        ],
        "payments-commerce": [
            {"title": "Solana Pay Plugin for Shopify", "description": "One-click Shopify integration for Solana Pay. Accept SOL, USDC, and any SPL token. Auto-convert to stablecoin. Lower fees than Stripe."},
            {"title": "Blinks Commerce SDK", "description": "SDK for embedding Solana Actions (Blinks) into any website or app. Let users buy, tip, or subscribe without leaving the page. Middleware for commerce."},
            {"title": "Cross-Border Payment API", "description": "API for businesses to send cross-border payments via Solana. USDC in, local currency out via off-ramp partners. 10x cheaper than SWIFT."},
        ],
        "liquid-staking": [
            {"title": "LST Yield Optimizer", "description": "Automatically rotate between Solana LSTs (mSOL, jitoSOL, bSOL, INF) based on real-time APY. Use Sanctum for instant swaps. Maximize staking yield."},
            {"title": "LST Risk Monitor", "description": "Dashboard tracking depeg risk, validator concentration, and smart contract risk for all Solana LSTs. Alert users when risk thresholds are breached."},
            {"title": "Restaking Protocol Dashboard", "description": "Unified view of emerging Solana restaking protocols. Compare yields, lock periods, slashing conditions. Help users make informed restaking decisions."},
        ],
        "defi-innovation": [
            {"title": "DeFi Position Manager", "description": "Unified interface to manage all Solana DeFi positions — LP on Orca, perps on Drift, lending on Marginfi. One dashboard, one-click rebalance."},
            {"title": "Intent-Based Trading API", "description": "Express trading intents ('buy SOL below $150 within 24h') and let solvers compete to fill them optimally. Built on Solana for instant settlement."},
            {"title": "On-Chain Strategy Vault", "description": "Automated DeFi strategy vaults on Solana. Deposit USDC, earn yield from delta-neutral strategies across Drift, Phoenix, and Jupiter. Fully on-chain."},
        ],
        "gaming-entertainment": [
            {"title": "Game Asset Bridge", "description": "Protocol for moving in-game assets between Solana games. Standardized NFT metadata, cross-game item compatibility. One inventory across all games."},
            {"title": "Tournament Platform", "description": "Decentralized tournament platform on Solana. Escrow entry fees, auto-distribute prizes, verify results on-chain. For competitive gaming and prediction games."},
            {"title": "Game State Compression SDK", "description": "SDK for storing game state on Solana using compression. Save player progress, leaderboards, and achievements on-chain at minimal cost."},
        ],
        "cross-chain": [
            {"title": "Bridge Aggregator", "description": "Compare bridge routes, fees, and speeds across Wormhole, Allbridge, deBridge, and others. Find the cheapest and fastest way to move assets to/from Solana."},
            {"title": "Cross-Chain Intent Solver", "description": "Submit cross-chain intents ('move 100 USDC from Ethereum to Solana cheapest') and let solvers compete. Abstract away bridge complexity."},
            {"title": "Multi-Chain Portfolio Tracker", "description": "Track your portfolio across Solana, Ethereum, Base, and other chains in one view. Auto-detect bridged assets. Show total PnL across all chains."},
        ],
    }

    return ideas_map.get(narrative["id"], [
        {"title": "Custom Monitoring Tool", "description": f"Build a specialized monitoring and analytics dashboard for {narrative['label']} activity on Solana."},
        {"title": "Developer SDK", "description": f"Create a developer SDK that simplifies building {narrative['label']}-related applications on Solana."},
        {"title": "Data API Service", "description": f"Provide a paid API service with curated data and insights about {narrative['label']} trends in the Solana ecosystem."},
    ])


def analyze_all(
    onchain_data: dict,
    github_data: dict,
    social_data: dict,
) -> dict[str, Any]:
    """Run full narrative analysis across all data sources."""
    narratives = []

    for nid, definition in NARRATIVE_DEFINITIONS.items():
        scored = score_narrative(nid, definition, onchain_data, github_data, social_data)
        if scored["signal_count"] > 0:
            scored["product_ideas"] = generate_product_ideas(scored)
            narratives.append(scored)

    # Sort by score descending
    narratives.sort(key=lambda x: x["score"], reverse=True)

    # Summary stats
    total_signals = sum(n["signal_count"] for n in narratives)
    active_narratives = [n for n in narratives if n["strength"] in ("strong", "very_strong")]

    # Market context
    market = social_data.get("market_data", {})

    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_narratives_detected": len(narratives),
            "active_narratives": len(active_narratives),
            "total_signals": total_signals,
            "sol_price": market.get("sol_price", 0),
            "sol_24h_change": market.get("sol_price_change_24h", 0),
            "solana_trending_count": market.get("solana_trending_count", 0),
        },
        "narratives": narratives,
        "methodology": {
            "data_sources": ["Solana RPC (on-chain activity)", "GitHub API (developer signals)", "CoinGecko (market data)", "RSS feeds (news signals)"],
            "signal_detection": "Pattern matching against 12 narrative definitions with weighted scoring. Each signal type (on-chain tx rate, repo stars, news mentions, trending coins) contributes differently to the overall score.",
            "ranking": "Narratives are ranked by composite signal score. Strength levels: very_strong (10+), strong (5-10), moderate (2-5), emerging (0.5-2), quiet (<0.5).",
            "update_frequency": "Data collected every 2 hours. Full analysis runs on each collection cycle.",
        },
    }

"""
Social and community signal collector.
Aggregates data from public sources: RSS feeds, public APIs, etc.
"""

import httpx
import asyncio
import re
from datetime import datetime, timezone
from typing import Any


# Public RSS / Atom feeds for Solana ecosystem news
RSS_FEEDS = [
    {"name": "Solana Blog", "url": "https://solana.com/news/rss.xml"},
    {"name": "Solana Status", "url": "https://status.solana.com/history.rss"},
    {"name": "CoinDesk Solana", "url": "https://www.coindesk.com/tag/solana/feed/"},
    {"name": "Blockworks", "url": "https://blockworks.co/feed"},
]

# Public API endpoints for market/ecosystem data
MARKET_APIS = {
    "coingecko_sol": "https://api.coingecko.com/api/v3/coins/solana",
    "coingecko_trending": "https://api.coingecko.com/api/v3/search/trending",
}

# Solana ecosystem keywords to track
NARRATIVE_KEYWORDS = [
    "token-2022", "token extensions", "confidential transfers",
    "compressed nft", "cnft", "state compression",
    "blink", "actions", "solana actions",
    "fire dancer", "firedancer",
    "mev", "jito", "sandwich", "priority fees",
    "depin", "helium", "hivemapper", "render",
    "ai agent", "autonomous agent", "agent economy",
    "paymaster", "gasless", "account abstraction",
    "restaking", "liquid staking", "lst",
    "rwa", "real world assets", "tokenization",
    "perpetuals", "perps", "derivatives",
    "prediction market", "futarchy",
    "zk compression", "light protocol",
    "mobile", "saga", "chapter 2",
    "payments", "solana pay",
    "gaming", "gamefi",
    "pump.fun", "memecoin", "bonding curve",
    "raydium", "orca", "jupiter",
    "tensor", "magic eden", "nft marketplace",
    "tip router", "ncn",
    "drift", "phoenix", "openbook",
    "sanctum", "infinite lst",
    "wormhole", "bridge", "cross-chain",
]


def extract_rss_items(xml_text: str) -> list[dict[str, str]]:
    """Simple RSS/Atom parser - extracts titles, links, dates."""
    items = []
    # Match <item> or <entry> blocks
    for match in re.finditer(r'<(?:item|entry)>(.*?)</(?:item|entry)>', xml_text, re.DOTALL):
        block = match.group(1)
        title = re.search(r'<title[^>]*>(.*?)</title>', block, re.DOTALL)
        link = re.search(r'<link[^>]*(?:href="([^"]*)")?[^>]*>(.*?)</link>', block, re.DOTALL)
        pub_date = re.search(r'<(?:pubDate|published|updated)>(.*?)</(?:pubDate|published|updated)>', block)

        link_url = ""
        if link:
            link_url = link.group(1) or link.group(2) or ""
            link_url = link_url.strip()

        items.append({
            "title": title.group(1).strip() if title else "",
            "link": link_url,
            "date": pub_date.group(1).strip() if pub_date else "",
        })
    return items


async def collect_rss_signals() -> list[dict[str, Any]]:
    """Collect signals from RSS feeds."""
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        for feed in RSS_FEEDS:
            try:
                resp = await client.get(feed["url"], follow_redirects=True)
                if resp.status_code == 200:
                    items = extract_rss_items(resp.text)
                    for item in items[:10]:
                        # Check for narrative keywords
                        text = (item.get("title", "") + " " + item.get("link", "")).lower()
                        matched_keywords = [k for k in NARRATIVE_KEYWORDS if k.lower() in text]
                        results.append({
                            "type": "rss_signal",
                            "source": feed["name"],
                            "title": item["title"],
                            "link": item["link"],
                            "date": item["date"],
                            "matched_narratives": matched_keywords,
                        })
            except Exception as e:
                results.append({
                    "type": "rss_signal",
                    "source": feed["name"],
                    "error": str(e),
                })
            await asyncio.sleep(0.5)
    return results


async def collect_market_signals() -> dict[str, Any]:
    """Collect SOL market data and trending coins."""
    result = {}
    async with httpx.AsyncClient(timeout=15) as client:
        # SOL price and market data
        try:
            resp = await client.get(MARKET_APIS["coingecko_sol"])
            if resp.status_code == 200:
                data = resp.json()
                market = data.get("market_data", {})
                result["sol_price"] = market.get("current_price", {}).get("usd", 0)
                result["sol_price_change_24h"] = market.get("price_change_percentage_24h", 0)
                result["sol_price_change_7d"] = market.get("price_change_percentage_7d", 0)
                result["sol_price_change_30d"] = market.get("price_change_percentage_30d", 0)
                result["sol_market_cap"] = market.get("market_cap", {}).get("usd", 0)
                result["sol_volume_24h"] = market.get("total_volume", {}).get("usd", 0)
                result["sol_ath"] = market.get("ath", {}).get("usd", 0)
                result["sol_ath_change_pct"] = market.get("ath_change_percentage", {}).get("usd", 0)

                # Developer data
                dev = data.get("developer_data", {})
                result["github_forks"] = dev.get("forks", 0)
                result["github_stars"] = dev.get("stars", 0)
                result["github_subscribers"] = dev.get("subscribers", 0)
                result["github_total_issues"] = dev.get("total_issues", 0)
                result["commit_count_4w"] = dev.get("commit_count_4_weeks", 0)

                # Community data
                community = data.get("community_data", {})
                result["twitter_followers"] = community.get("twitter_followers", 0)
                result["reddit_subscribers"] = community.get("reddit_subscribers", 0)

                # Sentiment
                result["sentiment_up"] = data.get("sentiment_votes_up_percentage", 0)
                result["sentiment_down"] = data.get("sentiment_votes_down_percentage", 0)
        except Exception as e:
            result["error"] = str(e)

        await asyncio.sleep(1)

        # Trending coins (to see if Solana ecosystem tokens are trending)
        try:
            resp = await client.get(MARKET_APIS["coingecko_trending"])
            if resp.status_code == 200:
                data = resp.json()
                trending_coins = []
                for coin_data in data.get("coins", []):
                    coin = coin_data.get("item", {})
                    platforms = coin.get("platforms", {})
                    is_solana = "solana" in str(platforms).lower() or \
                                "solana" in coin.get("name", "").lower() or \
                                "sol" in coin.get("symbol", "").lower()
                    trending_coins.append({
                        "name": coin.get("name", ""),
                        "symbol": coin.get("symbol", ""),
                        "market_cap_rank": coin.get("market_cap_rank"),
                        "is_solana_ecosystem": is_solana,
                    })
                result["trending_coins"] = trending_coins
                result["solana_trending_count"] = sum(
                    1 for c in trending_coins if c["is_solana_ecosystem"]
                )
        except Exception as e:
            result["trending_error"] = str(e)

    return result


async def collect_all() -> dict[str, Any]:
    """Run all social/community collectors."""
    rss_signals, market_signals = await asyncio.gather(
        collect_rss_signals(),
        collect_market_signals(),
    )
    return {
        "source": "social",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "rss_signals": rss_signals,
        "market_data": market_signals,
    }

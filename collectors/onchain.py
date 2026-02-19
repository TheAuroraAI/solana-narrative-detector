"""
On-chain signal collector for Solana.
Tracks program activity, new programs, and usage patterns.
"""

import httpx
import asyncio
import json
from datetime import datetime, timezone
from typing import Any


SOLANA_RPC = "https://api.mainnet-beta.solana.com"

# Well-known Solana programs to track activity on
TRACKED_PROGRAMS = {
    "JUP6LkMUJaRrnKjmpLA8UP3CjJmQhmGhrXuJq2e3mxCr": "Jupiter Aggregator",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca Whirlpool",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "Pump.fun",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "SPL Token",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s": "Metaplex Token Metadata",
    "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K": "Magic Eden v2",
    "TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN": "Tensor Swap",
    "DRiPPP2LytDmNUbPTjG75GBzfnGrovJRqgCSybiBPZuB": "DRiP",
    "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH": "Drift Protocol",
    "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD": "Marinade Finance",
    "SoLXmnP9JvL6vJ7TN1VqtTxqsc2izmPfF9CsMDEuRzJ": "Solana Name Service",
    "jCebN34bUfdeUYJT13J1yG16XWQpt5PDx6Mse9GUqhR": "SharkyFi",
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": "Phoenix",
    "SWiMDJYFUGj6cPrQ6QYYYWZtvXQdRChSVAygDZDsCHC": "Sanctum",
}

# Programs that indicate new ecosystem activity
INFRA_PROGRAMS = {
    "BPFLoaderUpgradeab1e11111111111111111111111": "BPF Upgradeable Loader",
}


async def get_recent_program_activity(rpc_url: str = SOLANA_RPC) -> list[dict[str, Any]]:
    """Get recent transaction counts for tracked programs."""
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        # Get recent slot for context
        slot_resp = await client.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot"
        })
        current_slot = slot_resp.json().get("result", 0)

        # Get performance samples (recent TPS data)
        perf_resp = await client.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getRecentPerformanceSamples",
            "params": [5]
        })
        perf_data = perf_resp.json().get("result", [])
        avg_tps = 0
        if perf_data:
            total_txs = sum(s.get("numTransactions", 0) for s in perf_data)
            total_secs = sum(s.get("samplePeriodSecs", 60) for s in perf_data)
            avg_tps = total_txs / max(total_secs, 1)

        results.append({
            "type": "network_overview",
            "current_slot": current_slot,
            "avg_tps": round(avg_tps, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Sample signatures for major programs (limited to avoid rate limits)
        for address, name in list(TRACKED_PROGRAMS.items())[:10]:
            try:
                sig_resp = await client.post(rpc_url, json={
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [address, {"limit": 20}]
                })
                sigs = sig_resp.json().get("result", [])
                if sigs:
                    # Calculate time span of these transactions
                    timestamps = [s.get("blockTime", 0) for s in sigs if s.get("blockTime")]
                    if len(timestamps) >= 2:
                        time_span = max(timestamps) - min(timestamps)
                        tx_rate = len(sigs) / max(time_span, 1) * 3600  # txs per hour
                    else:
                        tx_rate = 0
                        time_span = 0

                    results.append({
                        "type": "program_activity",
                        "program": name,
                        "address": address,
                        "recent_tx_count": len(sigs),
                        "tx_per_hour_estimate": round(tx_rate, 1),
                        "latest_block_time": max(timestamps) if timestamps else 0,
                        "has_errors": any(s.get("err") for s in sigs),
                    })
                await asyncio.sleep(0.2)  # Rate limiting
            except Exception as e:
                results.append({
                    "type": "program_activity",
                    "program": name,
                    "address": address,
                    "error": str(e),
                })

    return results


async def get_new_programs_deployed(rpc_url: str = SOLANA_RPC) -> list[dict[str, Any]]:
    """Check BPF loader for recent program deployments."""
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            sig_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    "BPFLoaderUpgradeab1e11111111111111111111111",
                    {"limit": 25}
                ]
            })
            sigs = sig_resp.json().get("result", [])
            for sig in sigs:
                results.append({
                    "type": "new_program_deploy",
                    "signature": sig.get("signature", ""),
                    "block_time": sig.get("blockTime", 0),
                    "slot": sig.get("slot", 0),
                    "success": sig.get("err") is None,
                })
        except Exception as e:
            results.append({"type": "new_program_deploy", "error": str(e)})
    return results


async def get_token_metrics(rpc_url: str = SOLANA_RPC) -> dict[str, Any]:
    """Get SOL supply and epoch info."""
    async with httpx.AsyncClient(timeout=30) as client:
        supply_resp = await client.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSupply"
        })
        epoch_resp = await client.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getEpochInfo"
        })
        supply = supply_resp.json().get("result", {}).get("value", {})
        epoch = epoch_resp.json().get("result", {})
        return {
            "type": "token_metrics",
            "total_supply_sol": round(supply.get("total", 0) / 1e9, 0),
            "circulating_sol": round(supply.get("circulating", 0) / 1e9, 0),
            "epoch": epoch.get("epoch", 0),
            "slot_index": epoch.get("slotIndex", 0),
            "slots_in_epoch": epoch.get("slotsInEpoch", 0),
            "epoch_progress_pct": round(epoch.get("slotIndex", 0) / max(epoch.get("slotsInEpoch", 1), 1) * 100, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def collect_all() -> dict[str, Any]:
    """Run all on-chain collectors and return combined results."""
    program_activity, new_programs, token_metrics = await asyncio.gather(
        get_recent_program_activity(),
        get_new_programs_deployed(),
        get_token_metrics(),
    )
    return {
        "source": "onchain",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "program_activity": program_activity,
        "new_programs": new_programs,
        "token_metrics": token_metrics,
    }

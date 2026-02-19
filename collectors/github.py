"""
GitHub signal collector for Solana ecosystem.
Tracks trending repos, new repos, and developer activity.
"""

import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any


GITHUB_API = "https://api.github.com"

# Key Solana ecosystem organizations to monitor
TRACKED_ORGS = [
    "solana-labs",
    "solana-foundation",
    "anza-xyz",
    "jito-foundation",
    "coral-xyz",
    "metaplex-foundation",
    "project-serum",
    "marinade-finance",
    "drift-labs",
    "tensor-hq",
    "helium",
    "clockwork-xyz",
    "switchboard-xyz",
    "squads-protocol",
    "jupiter-exchange",
]

# Search queries to discover trending Solana repos
SEARCH_QUERIES = [
    "solana created:>{date} language:rust",
    "solana anchor created:>{date}",
    "solana program created:>{date} language:typescript",
    "solana agent created:>{date}",
    "solana defi created:>{date}",
    "solana nft created:>{date}",
    "solana token-2022 created:>{date}",
    "solana blink created:>{date}",
    "solana compressed-nft created:>{date}",
    "solana mev created:>{date}",
]


async def search_trending_repos(
    days_back: int = 14,
    github_token: str | None = None,
) -> list[dict[str, Any]]:
    """Search for recently created Solana repos sorted by stars."""
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    date_cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    results = []

    async with httpx.AsyncClient(timeout=30) as client:
        for query_template in SEARCH_QUERIES[:6]:  # Limit to avoid rate limits
            query = query_template.format(date=date_cutoff)
            try:
                resp = await client.get(
                    f"{GITHUB_API}/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": 10},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for repo in data.get("items", []):
                        results.append({
                            "type": "trending_repo",
                            "name": repo["full_name"],
                            "description": repo.get("description", ""),
                            "stars": repo["stargazers_count"],
                            "forks": repo["forks_count"],
                            "language": repo.get("language", ""),
                            "created_at": repo["created_at"],
                            "updated_at": repo["updated_at"],
                            "topics": repo.get("topics", []),
                            "url": repo["html_url"],
                            "open_issues": repo["open_issues_count"],
                        })
                elif resp.status_code == 403:
                    # Rate limited
                    break
                await asyncio.sleep(2)  # GitHub search rate limit: 10 req/min
            except Exception as e:
                results.append({"type": "trending_repo", "error": str(e), "query": query})

    # Deduplicate by repo name
    seen = set()
    unique = []
    for r in results:
        name = r.get("name", "")
        if name and name not in seen:
            seen.add(name)
            unique.append(r)

    # Sort by stars
    unique.sort(key=lambda x: x.get("stars", 0), reverse=True)
    return unique[:50]


async def get_org_activity(
    github_token: str | None = None,
) -> list[dict[str, Any]]:
    """Get recent activity from key Solana organizations."""
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for org in TRACKED_ORGS[:8]:  # Limit for rate limits
            try:
                # Get org's recent repos
                resp = await client.get(
                    f"{GITHUB_API}/orgs/{org}/repos",
                    params={"sort": "updated", "per_page": 5},
                    headers=headers,
                )
                if resp.status_code == 200:
                    repos = resp.json()
                    for repo in repos:
                        results.append({
                            "type": "org_repo_activity",
                            "org": org,
                            "repo": repo["full_name"],
                            "description": repo.get("description", ""),
                            "stars": repo["stargazers_count"],
                            "updated_at": repo["updated_at"],
                            "language": repo.get("language", ""),
                            "open_issues": repo["open_issues_count"],
                        })
                elif resp.status_code == 403:
                    break
                await asyncio.sleep(1)
            except Exception as e:
                results.append({"type": "org_repo_activity", "org": org, "error": str(e)})

    return results


async def get_solana_repo_pulse(
    github_token: str | None = None,
) -> dict[str, Any]:
    """Get pulse data for the main Solana repos."""
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    key_repos = [
        "anza-xyz/agave",
        "solana-labs/solana-program-library",
        "coral-xyz/anchor",
        "jito-foundation/jito-solana",
        "metaplex-foundation/mpl-core",
    ]

    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for repo in key_repos:
            try:
                # Get recent commits
                since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
                resp = await client.get(
                    f"{GITHUB_API}/repos/{repo}/commits",
                    params={"since": since, "per_page": 5},
                    headers=headers,
                )
                if resp.status_code == 200:
                    commits = resp.json()
                    results.append({
                        "type": "repo_pulse",
                        "repo": repo,
                        "recent_commits": len(commits),
                        "latest_commit_date": commits[0]["commit"]["committer"]["date"] if commits else None,
                        "latest_commit_msg": commits[0]["commit"]["message"][:200] if commits else None,
                    })

                # Get open PRs count
                pr_resp = await client.get(
                    f"{GITHUB_API}/repos/{repo}/pulls",
                    params={"state": "open", "per_page": 1},
                    headers=headers,
                )
                if pr_resp.status_code == 200:
                    # Check Link header for total count
                    link = pr_resp.headers.get("Link", "")
                    if "last" in link:
                        import re
                        match = re.search(r'page=(\d+)>; rel="last"', link)
                        pr_count = int(match.group(1)) if match else len(pr_resp.json())
                    else:
                        pr_count = len(pr_resp.json())
                    results[-1]["open_prs"] = pr_count

                await asyncio.sleep(1)
            except Exception as e:
                results.append({"type": "repo_pulse", "repo": repo, "error": str(e)})

    return results


async def collect_all(github_token: str | None = None) -> dict[str, Any]:
    """Run all GitHub collectors."""
    trending, org_activity, pulse = await asyncio.gather(
        search_trending_repos(github_token=github_token),
        get_org_activity(github_token=github_token),
        get_solana_repo_pulse(github_token=github_token),
    )
    return {
        "source": "github",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "trending_repos": trending,
        "org_activity": org_activity,
        "repo_pulse": pulse,
    }

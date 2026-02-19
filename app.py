"""
Solana Narrative Detector — Main Application.
Collects signals from on-chain, GitHub, and social sources.
Detects emerging narratives and generates product ideas.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from collectors import onchain, github, social
from analyzer import analyze_all

load_dotenv()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Store the latest analysis in memory
latest_analysis: dict = {}
collection_history: list[dict] = []

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


async def run_collection_cycle():
    """Run a full data collection and analysis cycle."""
    global latest_analysis

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting collection cycle...")

    try:
        # Collect data from all sources in parallel
        onchain_data, github_data, social_data = await asyncio.gather(
            onchain.collect_all(),
            github.collect_all(github_token=GITHUB_TOKEN or None),
            social.collect_all(),
        )

        # Run analysis
        analysis = analyze_all(onchain_data, github_data, social_data)

        # Store results
        latest_analysis = analysis

        # Save to disk for persistence
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        with open(DATA_DIR / f"analysis_{timestamp}.json", "w") as f:
            json.dump(analysis, f, indent=2)

        # Keep only last 50 analyses on disk
        analysis_files = sorted(DATA_DIR.glob("analysis_*.json"))
        for old_file in analysis_files[:-50]:
            old_file.unlink()

        # Track history
        collection_history.append({
            "timestamp": analysis["analyzed_at"],
            "narratives_detected": analysis["summary"]["total_narratives_detected"],
            "total_signals": analysis["summary"]["total_signals"],
            "sol_price": analysis["summary"]["sol_price"],
        })
        # Keep last 100 history entries
        if len(collection_history) > 100:
            collection_history.pop(0)

        active = len([n for n in analysis["narratives"] if n["strength"] in ("strong", "very_strong")])
        print(f"[{datetime.now(timezone.utc).isoformat()}] Collection complete. "
              f"{analysis['summary']['total_narratives_detected']} narratives, "
              f"{active} active, {analysis['summary']['total_signals']} signals.")

    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Collection error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run initial collection and schedule periodic updates."""
    # Load most recent analysis from disk if available
    global latest_analysis
    analysis_files = sorted(DATA_DIR.glob("analysis_*.json"))
    if analysis_files:
        with open(analysis_files[-1]) as f:
            latest_analysis = json.load(f)
        print(f"Loaded previous analysis from {analysis_files[-1].name}")

    # Run initial collection
    await run_collection_cycle()

    # Schedule periodic collection every 2 hours
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_collection_cycle, "interval", hours=2)
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="Solana Narrative Detector",
    description="Detects emerging narratives in the Solana ecosystem from on-chain data, GitHub activity, and social signals.",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard showing detected narratives."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "analysis": latest_analysis,
        "history": collection_history[-20:],
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "last_analysis": latest_analysis.get("analyzed_at", "never"),
        "narratives_detected": latest_analysis.get("summary", {}).get("total_narratives_detected", 0),
    }


@app.get("/api/narratives")
async def get_narratives():
    """Get all detected narratives with scores and signals."""
    return JSONResponse(content=latest_analysis)


@app.get("/api/narratives/{narrative_id}")
async def get_narrative(narrative_id: str):
    """Get a specific narrative by ID."""
    for n in latest_analysis.get("narratives", []):
        if n["id"] == narrative_id:
            return JSONResponse(content=n)
    return JSONResponse(content={"error": "Narrative not found"}, status_code=404)


@app.get("/api/ideas")
async def get_all_ideas():
    """Get all product ideas across all narratives."""
    ideas = []
    for n in latest_analysis.get("narratives", []):
        for idea in n.get("product_ideas", []):
            ideas.append({
                "narrative": n["label"],
                "narrative_strength": n["strength"],
                **idea,
            })
    return JSONResponse(content={"ideas": ideas, "count": len(ideas)})


@app.get("/api/history")
async def get_history():
    """Get collection history."""
    return JSONResponse(content={"history": collection_history})


@app.post("/api/collect")
async def trigger_collection():
    """Manually trigger a collection cycle."""
    await run_collection_cycle()
    return JSONResponse(content={"status": "collection complete", "analyzed_at": latest_analysis.get("analyzed_at")})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

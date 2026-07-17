#!/usr/bin/env python3
"""Fetch TMDB posters for existing transfer records."""

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")

from app.models.db import Job, SessionLocal  # noqa: E402
from app.services.tmdb import TMDBClient  # noqa: E402


RELEASE_MARKERS = re.compile(
    r"\b(?:"
    r"S\d{1,2}(?:E\d{1,3})?|Season\s*\d+|Complete\s+Collection|"
    r"2160p|1080p|720p|480p|4K|UHD|BluRay|BRRip|BDRip|WEB(?:-DL|Rip)?|"
    r"HDTV|DVDRip|REMUX|HDR10?\+?|HDR|DV|Dolby\s*Vision|"
    r"x26[45]|H\.?26[45]|HEVC|AVC|10bit|"
    r"AAC|AC3|EAC3|DDP?\d(?:\.\d)?|DTS(?:-HD)?|Atmos|"
    r"YIFY|YTS|MeGusta|GalaxyRG|TGx"
    r")\b",
    re.IGNORECASE,
)


def extract_search_details(release_title: str) -> tuple[str, str]:
    """Convert a release filename into a likely title and release year."""
    normalized = re.sub(r"[._]+", " ", release_title)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    maximum_year = datetime.now().year + 1
    year = ""
    for match in re.finditer(r"\b(?:19|20)\d{2}\b", normalized):
        candidate = int(match.group())
        if candidate <= maximum_year:
            year = str(candidate)
            normalized = normalized[: match.start()]
            break

    normalized = re.sub(r"\[[^\]]*]", " ", normalized)
    normalized = re.sub(r"\([^)]*\)", " ", normalized)

    marker = RELEASE_MARKERS.search(normalized)
    if marker:
        normalized = normalized[: marker.start()]

    title = re.sub(r"[\s(\[{\-–—]+$", "", normalized)
    title = re.sub(r"\s+", " ", title).strip()
    return title or release_title, year


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def choose_result(
    results: list[dict[str, Any]],
    query_title: str,
    query_year: str,
    media_type: str,
) -> dict[str, Any] | None:
    """Select the closest result while rejecting weak or posterless matches."""
    candidates = [
        result
        for result in results
        if result.get("media_type") == media_type and result.get("poster_path")
    ]
    if not candidates:
        return None

    normalized_query = normalize_title(query_title)

    def score(result: dict[str, Any]) -> float:
        title_score = SequenceMatcher(
            None, normalized_query, normalize_title(result.get("title", ""))
        ).ratio()
        if query_year and result.get("year") == query_year:
            title_score += 0.25
        elif query_year and result.get("year"):
            title_score -= 0.10
        return title_score

    best = max(candidates, key=score)
    return best if score(best) >= 0.55 else None


async def backfill(args: argparse.Namespace) -> int:
    if not os.getenv("TMDB_API_KEY"):
        print("TMDB_API_KEY is not configured in .env.", file=sys.stderr)
        return 1

    db = SessionLocal()
    client = TMDBClient()
    cache: dict[tuple[str, str, str], dict[str, Any] | None] = {}
    updated = 0
    unmatched = 0

    try:
        query = db.query(Job).filter(Job.status == args.status)
        if not args.force:
            query = query.filter((Job.poster_path.is_(None)) | (Job.poster_path == ""))
        query = query.order_by(Job.created_at.asc())
        if args.limit:
            query = query.limit(args.limit)
        jobs = query.all()

        print(f"Found {len(jobs)} {args.status} transfer(s) to inspect.")

        for job in jobs:
            title, year = extract_search_details(job.title)
            media_type = job.media_type if job.media_type in {"movie", "tv"} else "movie"
            cache_key = (title.lower(), year, media_type)

            if cache_key not in cache:
                results = await client.search(title)
                cache[cache_key] = choose_result(results, title, year, media_type)
                if args.delay:
                    await asyncio.sleep(args.delay)

            match = cache[cache_key]
            if not match:
                unmatched += 1
                print(f"NO MATCH  {job.title!r} (searched: {title!r} {year})")
                continue

            print(
                f"MATCH     {job.title!r} -> "
                f"{match['title']!r} ({match.get('year') or 'unknown year'})"
            )
            if not args.dry_run:
                job.poster_path = match["poster_path"]
                db.commit()
            updated += 1

        action = "Would update" if args.dry_run else "Updated"
        print(f"{action} {updated} transfer(s); {unmatched} had no confident match.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill missing TMDB poster paths in the tvbox jobs database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matches without updating the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch posters even when a transfer already has one.",
    )
    parser.add_argument(
        "--status",
        default="completed",
        help="Only process this transfer status (default: completed).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most this many transfers (default: all).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Seconds between TMDB requests (default: 0.25).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(backfill(parse_args())))

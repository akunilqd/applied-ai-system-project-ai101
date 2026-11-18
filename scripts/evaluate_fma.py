"""Evaluate the FMA retrieval and ranking pipeline without calling Gemini."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "songs_fma.csv"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag import retrieve_and_rank
from src.recommender import load_songs


BLOCKED_TERMS = re.compile(
    r"\b(interview|podcast|spoken word|radio show|speech|commentary)\b",
    re.IGNORECASE,
)

CASES = [
    {
        "name": "calm folk study",
        "query": "calm acoustic folk music for studying",
        "preferences": {
            "genre": "folk",
            "mood": "calm",
            "energy": 0.3,
            "acousticness": 0.9,
        },
        "expected_genre": "folk",
    },
    {
        "name": "energetic electronic workout",
        "query": "energetic electronic music for working out",
        "preferences": {
            "genre": "electronic",
            "mood": "intense",
            "energy": 0.9,
            "danceability": 0.8,
        },
        "expected_genre": "electronic",
    },
    {
        "name": "sad folk evening",
        "query": "sad relaxing folk music",
        "preferences": {
            "genre": "folk",
            "mood": "sad",
            "energy": 0.3,
            "valence": 0.2,
            "acousticness": 0.8,
        },
        "expected_genre": "folk",
    },
]


def evaluate_case(case, songs):
    results = retrieve_and_rank(
        case["query"],
        case["preferences"],
        songs,
        k=5,
        candidate_k=50,
    )
    titles = [row[0]["title"] for row in results]
    genres = [row[0]["genre"] for row in results]
    genre_hits = sum(genre == case["expected_genre"] for genre in genres)
    blocked_hits = sum(bool(BLOCKED_TERMS.search(title)) for title in titles)
    if len(results) != 5:
        raise AssertionError(f"expected 5 results, got {len(results)}")
    if genre_hits < 4:
        raise AssertionError(f"only {genre_hits}/5 results matched expected genre")
    if blocked_hits:
        raise AssertionError(f"blocked spoken-word title returned: {titles}")
    return genre_hits, titles[:3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    songs = load_songs(CATALOG)
    passed = 0
    cases = []
    for case in CASES:
        try:
            genre_hits, top_titles = evaluate_case(case, songs)
            passed += 1
            cases.append({
                "case": case["name"],
                "passed": True,
                "genre_hits": genre_hits,
                "top_titles": top_titles,
            })
            print(f"PASS {case['name']}: {genre_hits}/5 genre hits; top={top_titles}")
        except AssertionError as error:
            cases.append({
                "case": case["name"],
                "passed": False,
                "detail": str(error),
            })
            print(f"FAIL {case['name']}: {error}")
    print(f"FMA evaluation: {passed}/{len(CASES)} passed")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({
            "passed": passed,
            "total": len(CASES),
            "catalog": str(CATALOG),
            "cases": cases,
        }, indent=2) + "\n", encoding="utf-8")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())

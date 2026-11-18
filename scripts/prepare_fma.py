"""Prepare a normalized FMA catalog for VibeFinder."""

from __future__ import annotations

import argparse
import ast
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_DIR = ROOT / "data" / "fma_metadata"
DEFAULT_OUTPUT = ROOT / "data" / "songs_fma.csv"

OUTPUT_COLUMNS = [
    "id",
    "title",
    "artist",
    "genre",
    "tags",
    "energy",
    "tempo_bpm",
    "valence",
    "danceability",
    "acousticness",
    "duration_seconds",
    "release_year",
    "source",
    "license",
]

ECHONEST_FIELDS = {
    "energy": "echonest__audio_features__energy",
    "tempo_bpm": "echonest__audio_features__tempo",
    "valence": "echonest__audio_features__valence",
    "danceability": "echonest__audio_features__danceability",
    "acousticness": "echonest__audio_features__acousticness",
}

# FMA contains spoken-word recordings mixed with music. They are not useful
# candidates for a music recommender, so remove them during catalog creation.
BLOCKED_GENRES = {
    "spoken",
    "spoken word",
    "comedy",
    "novelty",
}
BLOCKED_TERMS = (
    "interview",
    "podcast",
    "spoken word",
    "radio show",
    "speech",
    "commentary",
)


def flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert FMA's three-level headers into simple names."""
    frame = frame.copy()
    names = []
    for column in frame.columns:
        parts = [
            str(part).strip()
            for part in column
            if str(part).strip() and not str(part).startswith("Unnamed")
        ]
        names.append("__".join(parts))
    frame.columns = names
    frame.index.name = "id"
    return frame


def load_fma_tables(metadata_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the FMA tracks table and optional Echo Nest features."""
    metadata_dir = Path(metadata_dir)
    tracks = pd.read_csv(
        metadata_dir / "tracks.csv",
        header=[0, 1, 2],
        index_col=0,
        low_memory=False,
    )
    echonest = pd.read_csv(
        metadata_dir / "echonest.csv",
        header=[0, 1, 2],
        index_col=0,
        low_memory=False,
    )
    tracks = flatten_columns(tracks)
    echonest = flatten_columns(echonest)
    tracks.index = pd.to_numeric(tracks.index, errors="raise").astype("int64")
    echonest.index = pd.to_numeric(echonest.index, errors="raise").astype("int64")
    return tracks, echonest


def optional_number(value):
    """Convert an optional CSV value to a finite float or None."""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def optional_integer(value):
    """Convert an optional value to an integer or None."""
    number = optional_number(value)
    return int(number) if number is not None else None


def text_value(value, default=""):
    """Return trimmed text for a possibly missing value."""
    if value is None or pd.isna(value):
        return default
    return str(value).strip()


def list_value(value):
    """Turn FMA list-like fields such as ['rock', 'indie'] into text."""
    text = text_value(value)
    if not text:
        return ""
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return text.strip("[]")
    if isinstance(parsed, (list, tuple, set)):
        return " ".join(str(item).strip() for item in parsed)
    return str(parsed).strip()


def release_year(value):
    """Extract a release year from FMA's date field."""
    text = text_value(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed.year)


def normalize_row(track_id, track, features) -> dict:
    """Map one FMA record into the VibeFinder catalog schema."""
    tags = " ".join(
        part
        for part in (
            list_value(track.get("track__tags")),
            list_value(track.get("artist__tags")),
            list_value(track.get("album__tags")),
            list_value(track.get("track__genres_all")),
        )
        if part
    )
    row = {
        "id": int(track_id),
        "title": text_value(track.get("track__title"), "unknown title"),
        "artist": text_value(track.get("artist__name"), "unknown artist"),
        "genre": text_value(track.get("track__genre_top"), "unknown").casefold(),
        "tags": tags.casefold(),
        "energy": optional_number(features.get(ECHONEST_FIELDS["energy"])),
        "tempo_bpm": optional_number(features.get(ECHONEST_FIELDS["tempo_bpm"])),
        "valence": optional_number(features.get(ECHONEST_FIELDS["valence"])),
        "danceability": optional_number(features.get(ECHONEST_FIELDS["danceability"])),
        "acousticness": optional_number(features.get(ECHONEST_FIELDS["acousticness"])),
        "duration_seconds": optional_integer(track.get("track__duration")),
        "release_year": release_year(track.get("album__date_released")),
        "source": "free-music-archive",
        "license": text_value(track.get("track__license"), "unknown"),
    }
    return row


def is_music_track(row: dict) -> bool:
    """Return False for obvious spoken-word or broadcast recordings."""
    genre = text_value(row.get("genre")).casefold()
    searchable_text = " ".join(
        text_value(row.get(field))
        for field in ("title", "artist", "genre", "tags")
    ).casefold()
    if genre in BLOCKED_GENRES:
        return False
    return not any(
        re.search(rf"\b{re.escape(term)}\b", searchable_text)
        for term in BLOCKED_TERMS
    )


def filter_tracks(rows: list[dict], allowed_genres=None, limit=None) -> list[dict]:
    """Keep music tracks, optionally filter genre, and keep ID order."""
    rows = [row for row in rows if is_music_track(row)]
    if allowed_genres:
        allowed = {genre.strip().casefold() for genre in allowed_genres}
        rows = [row for row in rows if row["genre"] in allowed]
    rows = sorted(rows, key=lambda row: row["id"])
    return rows[:limit] if limit is not None else rows


def prepare_dataset(metadata_dir, output_path, limit=None, allowed_genres=None) -> int:
    """Create the normalized CSV and return the number of written tracks."""
    tracks, echonest = load_fma_tables(metadata_dir)
    feature_columns = [
        column for column in ECHONEST_FIELDS.values() if column in echonest.columns
    ]
    feature_table = echonest[feature_columns]
    rows = []
    for track_id, track in tracks.iterrows():
        features = feature_table.loc[track_id] if track_id in feature_table.index else {}
        rows.append(normalize_row(track_id, track, features))
    rows = filter_tracks(rows, allowed_genres=allowed_genres, limit=limit)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)
    return len(rows)


def main() -> None:
    """Parse arguments and generate the normalized FMA catalog."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--genre", action="append", dest="genres")
    args = parser.parse_args()
    count = prepare_dataset(
        args.metadata_dir,
        args.output,
        limit=args.limit,
        allowed_genres=args.genres,
    )
    print(f"Wrote {count} songs to {args.output}")


if __name__ == "__main__":
    main()


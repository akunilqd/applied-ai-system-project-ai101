"""Deterministic, explainable content-based music recommendation."""

import csv
import math
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Song:
    """A fictional track; numeric audio attributes are synthetic estimates."""

    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    instrumentalness: float = 0.0
    popularity: float = 50.0
    release_year: int = 2020
    duration_seconds: int = 210
    language: str = "english"
    explicit: bool = False
    tags: str = ""
    source: str = ""
    license: str = ""


@dataclass(frozen=True)
class UserProfile:
    """Compatibility interface for the starter's object-oriented API."""

    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

    def preferences(self):
        """Translate the starter profile into the shared scoring interface."""
        return {"genre": self.favorite_genre, "mood": self.favorite_mood,
                "energy": self.target_energy,
                "acousticness": 1.0 if self.likes_acoustic else 0.0}


# Feature: (minimum, maximum, distance scale). Scores reward proximity.
NUMERIC = {
    "energy": (0, 1, 1), "tempo_bpm": (20, 300, 100),
    "valence": (0, 1, 1), "danceability": (0, 1, 1),
    "acousticness": (0, 1, 1), "instrumentalness": (0, 1, 1),
    "popularity": (0, 100, 100), "release_year": (1900, 2100, 50),
    "duration_seconds": (1, 3600, 300),
}


@dataclass(frozen=True)
class RankingStrategy:
    """Strategy pattern: interchangeable weights, one shared scoring engine."""

    genre: float
    mood: float
    energy: float

    def weight(self, feature):
        """Return this strategy's weight for a preference feature."""
        return {"genre": self.genre, "mood": self.mood,
                "energy": self.energy, "tempo_bpm": 1.0}.get(feature, 0.5)


STRATEGIES = {
    "genre-first": RankingStrategy(2.0, 1.0, 1.0),
    "mood-first": RankingStrategy(0.5, 3.0, 1.0),
    "energy-first": RankingStrategy(1.0, 1.0, 2.0),
}


LEGACY_SONG_COLUMNS = {
    "id", "title", "artist", "genre", "mood", "energy", "tempo_bpm",
    "valence", "danceability", "acousticness", "instrumentalness",
    "popularity", "release_year", "duration_seconds", "language", "explicit",
}

FMA_SONG_COLUMNS = {
    "id", "title", "artist", "genre", "tags", "energy", "tempo_bpm",
    "valence", "danceability", "acousticness", "duration_seconds",
    "release_year", "source", "license",
}


def _optional_number(value, *, integer=False):
    """Convert an optional CSV value without inventing a numeric default."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(number):
        return None
    if integer and not number.is_integer():
        return None
    return int(number) if integer else number


def _optional_bounded(value, low, high, *, integer=False):
    """Keep an optional number only when it fits the shared schema range."""
    number = _optional_number(value, integer=integer)
    if number is None or not low <= number <= high:
        return None
    return number


def _derived_mood(energy, valence):
    """Create a transparent coarse mood label from available FMA features."""
    if energy is None and valence is None:
        return "unknown"
    if energy is not None and energy >= 0.75:
        return "intense"
    if valence is not None and valence < 0.4:
        return "sad"
    if energy is not None and energy < 0.45:
        return "calm"
    if valence is not None and valence >= 0.6:
        return "happy"
    return "neutral"


def _normalize_fma_song(row):
    """Map a normalized FMA row into the shared Song schema."""
    energy = _optional_bounded(row.get("energy"), 0, 1)
    valence = _optional_bounded(row.get("valence"), 0, 1)
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "artist": row.get("artist"),
        "genre": row.get("genre", "unknown"),
        "mood": _derived_mood(energy, valence),
        "energy": energy,
        "tempo_bpm": _optional_bounded(row.get("tempo_bpm"), 20, 300),
        "valence": valence,
        "danceability": _optional_bounded(row.get("danceability"), 0, 1),
        "acousticness": _optional_bounded(row.get("acousticness"), 0, 1),
        "instrumentalness": None,
        "popularity": 50.0,
        "release_year": _optional_bounded(row.get("release_year"), 1900, 2100, integer=True),
        "duration_seconds": _optional_bounded(row.get("duration_seconds"), 1, 3600, integer=True),
        "language": "unknown",
        "explicit": False,
        "tags": row.get("tags", ""),
        "source": row.get("source", "free-music-archive"),
        "license": row.get("license", "unknown"),
    }


def bounded_number(value, name, low, high, *, integer=False):
    """Reject booleans, nonfinite values, and values outside an inclusive range."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, not a boolean")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    if integer and not number.is_integer():
        raise ValueError(f"{name} must be an integer")
    return int(number) if integer else number


def normalized_text(value, name):
    """Normalize categorical values while rejecting empty or nontext input."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value.strip().casefold()


def validate_preferences(prefs):
    """Validate a profile, including typo detection and optional feature ranges."""
    if not isinstance(prefs, dict):
        raise ValueError("profile must be a JSON object")
    unknown = set(prefs) - (set(NUMERIC) | {"genre", "mood", "language"})
    if unknown:
        raise ValueError(f"unknown preference(s): {', '.join(sorted(unknown))}")
    missing = {"genre", "mood", "energy"} - set(prefs)
    if missing:
        raise ValueError(f"missing preference(s): {', '.join(sorted(missing))}")
    result = {}
    for name, value in prefs.items():
        if name in NUMERIC:
            low, high, _ = NUMERIC[name]
            result[name] = bounded_number(value, name, low, high)
        else:
            result[name] = normalized_text(value, name)
    return result


def validate_song(song):
    """Normalize one song and validate all catalog attributes."""
    try:
        result = asdict(Song(**song))
    except TypeError as error:
        raise ValueError(f"invalid song schema: {error}") from None
    result["id"] = bounded_number(result["id"], "id", 1, 10**9, integer=True)
    for name in ("title", "artist", "genre", "mood", "language"):
        normalized = normalized_text(result[name], name)
        result[name] = result[name].strip() if name in {"title", "artist"} else normalized
    for name, (low, high, _) in NUMERIC.items():
        if result[name] is None or (isinstance(result[name], str) and not result[name].strip()):
            result[name] = None
            continue
        result[name] = bounded_number(result[name], name, low, high,
                                      integer=name in {"release_year", "duration_seconds"})
    if isinstance(result["explicit"], str):
        value = result["explicit"].strip().lower()
        if value not in {"true", "false"}:
            raise ValueError("explicit must be true or false")
        result["explicit"] = value == "true"
    if not isinstance(result["explicit"], bool):
        raise ValueError("explicit must be true or false")
    return result


def validate_catalog(songs):
    """Reject malformed tracks and duplicate IDs before ranking."""
    result, seen = [], set()
    for index, song in enumerate(songs, start=1):
        try:
            clean = validate_song(song)
            if clean["id"] in seen:
                raise ValueError(f"duplicate song id {clean['id']}")
        except ValueError as error:
            raise ValueError(f"song {index}: {error}") from None
        seen.add(clean["id"])
        result.append(clean)
    return result


def load_songs(csv_path: str | Path):
    """Load the legacy or normalized FMA CSV schema."""
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or ())
        if (headers != LEGACY_SONG_COLUMNS and headers != FMA_SONG_COLUMNS) or (
                len(reader.fieldnames or ()) != len(headers)):
            raise ValueError("CSV headers must match the legacy or normalized FMA Song schema")
        rows = list(reader)
    if not rows:
        raise ValueError("song catalog is empty")
    if headers == FMA_SONG_COLUMNS:
        rows = [_normalize_fma_song(row) for row in rows]
    return validate_catalog(rows)


def get_strategy(mode):
    """Resolve a ranking mode with a useful error for invalid names."""
    if mode not in STRATEGIES:
        raise ValueError(f"unknown mode {mode!r}; choose {', '.join(STRATEGIES)}")
    return STRATEGIES[mode]


def _score(prefs, song, strategy):
    """Compute weighted feature contributions and their matching explanations."""
    contributions, reasons = [], []
    for name, target in prefs.items():
        weight = strategy.weight(name)
        if name in NUMERIC:
            if song[name] is None:
                contributions.append(0.0)
                reasons.append(f"{name} unavailable (+0.000)")
                continue
            similarity = max(0.0, 1.0 - abs(song[name] - target) / NUMERIC[name][2])
            points = weight * similarity
            reason = f"{name} {song[name]:g} vs {target:g} (+{points:.3f})"
        else:
            if target == "unknown":
                points = 0.0
                reason = f"{name} unspecified (+{points:.3f})"
            else:
                matches = song[name] == target
                points = weight if matches else 0.0
                reason = f"{name} {'match' if matches else 'mismatch'} (+{points:.3f})"
        contributions.append(points)
        reasons.append(reason)
    return math.fsum(contributions), reasons


def score_song(user_prefs, song, mode="genre-first"):
    """Return a numeric score and exact feature-based reasons for one song."""
    return _score(validate_preferences(user_prefs), validate_song(song), get_strategy(mode))


def recommend_songs(user_prefs, songs, k=5, mode="genre-first", artist_penalty=0.0):
    """Greedily rank by score minus repeated-artist cost, with ID tie-breaking."""
    prefs = validate_preferences(user_prefs)
    catalog = validate_catalog(songs)
    strategy = get_strategy(mode)
    k = bounded_number(k, "k", 1, 100, integer=True)
    penalty = bounded_number(artist_penalty, "artist_penalty", 0, 10)
    remaining = [(song, *_score(prefs, song, strategy)) for song in catalog]
    result, counts = [], Counter()
    while remaining and len(result) < k:
        chosen = min(remaining, key=lambda row: (
            -(row[1] - penalty * counts[row[0]["artist"].casefold()]), row[0]["id"]))
        song, base, reasons = chosen
        artist = song["artist"].casefold()
        cost = penalty * counts[artist]
        details = reasons + ([f"repeat artist penalty (-{cost:.3f})"] if cost else [])
        result.append((song, base - cost, "; ".join(details)))
        counts[artist] += 1
        remaining.remove(chosen)
    return result


class Recommender:
    """Starter OOP adapter delegating to the same functional scoring engine."""

    def __init__(self, songs: list[Song]):
        self.songs = list(songs)
        self._catalog = validate_catalog([asdict(song) for song in self.songs])

    def recommend(self, user: UserProfile, k: int = 5) -> list[Song]:
        """Return Song objects ordered by the shared scoring function."""
        return [Song(**row[0]) for row in recommend_songs(user.preferences(), self._catalog, k)]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Explain a track's base score using the actual scoring contributions."""
        return "; ".join(score_song(user.preferences(), asdict(song))[1])

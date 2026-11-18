# VibeFinder System Design

## Goal

Extend the original 24-track VibeFinder content-based recommender into a working natural-language music search system using the Free Music Archive metadata catalog, TF-IDF retrieval, Gemini structured parsing, deterministic scoring, reliability checks, and a browser UI.

## Runtime flow

```text
browser prompt
  -> web/server.py /api/recommend
  -> GeminiQueryParser.parse()
  -> validated preferences + retrieval_query + keywords
  -> SongRetriever: TF-IDF and cosine similarity
  -> candidate tracks
  -> recommend_songs(): score, rank, artist penalty
  -> check_output(): guardrail
  -> JSON response
  -> web/app.js renders cards and player state
```

Gemini does not choose track IDs or calculate final scores. It translates language into bounded preferences. Python remains the source of truth for retrieval, ranking, explanations, and validation.

## Data

`data/songs_fma.csv` is a normalized 5,000-row catalog produced by `scripts/prepare_fma.py` from FMA metadata. Each row contains:

```text
id,title,artist,genre,tags,energy,tempo_bpm,valence,
danceability,acousticness,duration_seconds,release_year,source,license
```

Rows with obvious spoken-word/broadcast terms are removed. Missing numeric features remain missing; scoring gives them zero contribution rather than inventing measurements.

## Retrieval

`src/rag.py` converts each song into searchable text from title, artist, genre, tags, and derived mood. `TfidfVectorizer` uses English stop words and unigram/bigram features. Cosine similarity returns positive-scoring candidates in deterministic score/ID order. The current index is built in memory for each request; a persisted vector database is not required for this 5,000-row educational catalog.

## Gemini parser

`src/query_parser.py` uses `google-genai` structured output with a schema containing:

- categorical: `genre`, `mood`;
- bounded numeric targets: `energy`, `tempo_bpm`, `valence`, `danceability`, `acousticness`;
- retrieval fields: `retrieval_query`, `keywords`.

The output is passed through `validate_preferences()`. Unknown categorical values are treated as unspecified. The API key is read from `.env` on the server side only.

## Scoring

For a categorical field, a match earns the strategy weight. For a numeric field:

```text
similarity = max(0, 1 - abs(song_value - target_value) / distance_scale)
points = strategy_weight * similarity
```

The default `genre-first` weights are genre `2`, mood `1`, energy `1`, tempo `1`, and other optional numeric fields `0.5`. Repeated artists receive the configured penalty. Explanations are generated from these same contributions.

## Reliability

The project has two reliability layers:

1. `src.recommender` validates schemas, ranges, headers, IDs, preferences, and missing values.
2. `src.reliability.check_output()` verifies catalog membership, uniqueness, count, score arithmetic, ordering, and exact explanations. `src.rag.retrieve_and_rank()` now runs this guardrail on the live FMA/Gemini path.

The evaluation scripts also check constraints, blocked content, genre hit rate, and deterministic behavior.

## UI and audio

`web/server.py` serves `web/index.html`, `web/styles.css`, and `web/app.js` and exposes one JSON endpoint. The UI has a prompt form, interpretation chips, result rows, loading/error states, and a bottom audio-player dock. The current normalized catalog does not contain verified `audio_url` values, so the player remains disabled until a licensed preview source is added.

## Key files

```text
data/songs_fma.csv       normalized FMA catalog
scripts/prepare_fma.py   metadata normalization and filtering
scripts/evaluate_fma.py  offline FMA evaluation harness
src/query_parser.py     Gemini structured preference extraction
src/rag.py               TF-IDF retrieval and live guardrail call
src/recommender.py       deterministic scoring and ranking
src/reliability.py       output and constraint guardrails
web/server.py            local backend and API endpoint
web/                     browser UI
tests/                   regression and behavior coverage
docs/architecture.mmd    Mermaid architecture source
```

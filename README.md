# VibeFinder — Applied AI Music Recommender

VibeFinder is a content-based music recommendation system extended for Project 4. A user describes the sound they want in natural language; Gemini converts the request into validated music preferences; TF-IDF retrieves candidate tracks from a cleaned Free Music Archive catalog; and a deterministic scorer ranks and explains the results.

## 1. Base project and original scope

The base project was a small VibeFinder recommender built around 24 fictional songs. Its original goal was to demonstrate content-based ranking: compare a listener profile with song attributes, rank matches, explain each score, and vary the ranking with genre-first, mood-first, or energy-first strategies. The original CLI remains available through `src.main` as a regression baseline.

## 2. Project 4 additions

- **FMA catalog:** `data/songs_fma.csv` contains 5,000 normalized tracks with genre, tags, audio features, source, and license fields.
- **Custom RAG:** `src.rag` builds a TF-IDF index over title, artist, genre, tags, and derived mood. Cosine similarity retrieves up to 50 candidates.
- **Gemini specialization:** `src.query_parser` uses structured JSON output to extract genre, mood, energy, tempo, valence, danceability, acousticness, retrieval keywords, and an expanded retrieval query.
- **Deterministic ranking:** the existing scoring rules remain the source of truth for final scores and explanations.
- **Reliability:** catalog validation, bounded preferences, blocked spoken-word filtering, score/explanation checks, duplicate checks, and constraint handling.
- **Web demonstration:** `web/server.py` serves the single-page UI and the `/api/recommend` endpoint. The browser never receives the Gemini API key.

## 3. Actual architecture

See [diagrams/architecture.mmd](diagrams/architecture.mmd) for the required Mermaid source diagram and [docs/project4_evidence.md](docs/project4_evidence.md) for rubric evidence.

```text
browser prompt
  -> web/server.py
  -> Gemini structured parser
  -> validated preferences + expanded query
  -> TF-IDF candidate retrieval
  -> deterministic score/rank + output guardrail
  -> JSON recommendations
  -> browser cards and player dock
```

## 4. Setup

Use Python 3.10+.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a Gemini API key. Never commit `.env`.

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-flash-lite-latest
```

The lite model is used for short preference extraction. The model can be changed without modifying source code.

## 5. Run the system

### Web application

```powershell
.\.venv\Scripts\python.exe -m web.server
```

Open <http://127.0.0.1:8000>.

Enter prompts such as:

```text
calm acoustic folk music for studying
energetic electronic music for working out
sad piano music for a rainy evening
```

### Original baseline CLI

```powershell
.\.venv\Scripts\python.exe -m src.main --profile pop
```

### Live Gemini smoke test

```powershell
.\.venv\Scripts\python.exe test.py
```

## 6. Test and evaluation

Pytest uses a project-local temporary directory to avoid Windows permission errors in the default system temp folder.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run the original reliability/evaluation harness:

```powershell
.\.venv\Scripts\python.exe -m src.evaluate --report docs/evaluation.json
```

Run the FMA retrieval harness without spending Gemini API quota:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_fma.py --report docs/fma_evaluation.json
```

Expected FMA summary:

```text
PASS calm folk study: 5/5 genre hits
PASS energetic electronic workout: 5/5 genre hits
PASS sad folk evening: 5/5 genre hits
FMA evaluation: 3/3 passed
```

## 7. Reproducible end-to-end demo evidence

The following captured interactions use the same web pipeline: Gemini parser -> TF-IDF retrieval -> deterministic scoring. Results can vary slightly when Gemini returns different valid numeric estimates, but every result is still validated before display. Full evidence is in [docs/demo_evidence.md](docs/demo_evidence.md).

### Example 1 — calm acoustic study music

```text
Input: calm acoustic folk music for studying
Gemini preferences: genre=folk, mood=calm, energy=0.3, acousticness=0.9
Retrieval query: calm acoustic folk music for studying and concentration

Top recommendations:
1. Finale / folk
2. Heart On Fire / folk
3. Music of The Ages / folk
```

### Example 2 — energetic workout music

```text
Input: energetic electronic music for workout
Gemini preferences: genre=electronic, mood=intense, energy=0.9
Keywords: electronic, workout, energetic, upbeat, gym, dance

Top recommendation:
02 opendoor.mp3 / electronic / score 3.973
Reason: genre match (+2.000); energy 0.87344 vs 0.9 (+0.973); mood match (+1.000)
```

### Example 3 — sad relaxing folk music

```text
Input: sad relaxing folk music
Gemini preferences: genre=folk, mood=sad, energy=0.3, valence=0.2, acousticness=0.8

Top recommendations:
1. Make It Last / folk
2. Forever / folk
3. Kokopelli / folk
```

### Web command used for the demonstration

```powershell
.\.venv\Scripts\python.exe -m web.server
# Open http://127.0.0.1:8000
```

## 8. Scoring rules

Gemini does not produce the final recommendation score. It produces target preferences. The existing scorer then applies:

```text
categorical match: strategy weight
numeric feature: weight * max(0, 1 - abs(song_value - target) / scale)
adjusted score: base score - artist_penalty * previous_artist_count
```

The default `genre-first` weights are genre `2.0`, mood `1.0`, energy `1.0`, tempo `1.0`, and other optional numeric fields `0.5`. Missing FMA features contribute zero instead of being invented. A preference value of `unknown` is treated as unspecified and earns no match points.

## 9. Reliability evidence

The system rejects malformed profiles, out-of-range values, duplicate IDs, foreign tracks, duplicate recommendations, score drift, false explanations, and invalid ordering. It also removes obvious `Interview`, `Podcast`, `Spoken Word`, `Radio Show`, `Speech`, and `Commentary` records during FMA preparation.

Examples are documented in [docs/project4_evidence.md](docs/project4_evidence.md), while the original guardrail examples remain in [docs/examples.md](docs/examples.md).

## 10. Audio status

The UI includes an audio player dock and is ready for an `audio_url` field. The normalized catalog currently contains metadata and features, not verified audio stream URLs. The player therefore reports that no preview URL is available instead of fabricating a link. Adding a licensed, verified preview source is the next media-data step.

## 11. Limitations and future work

- FMA is a research/Creative Commons catalog, not a Spotify US-UK catalog.
- TF-IDF matches vocabulary; it does not understand every semantic synonym.
- Gemini estimates preferences from language; those estimates are not measured audio truth.
- The catalog has missing features and occasional weak metadata such as `Title Unknown`.
- The current evaluation measures rule consistency and genre hit rate, not listener satisfaction.
- Future work: add verified audio URLs, collect listener feedback, learn weights from ratings, and compare TF-IDF with embedding retrieval.

## 12. AI collaboration reflection

AI helped inspect the starter project, design the FMA normalization, write tests, debug Windows pytest permissions, design the UI, and integrate structured Gemini parsing. I accepted the shared-scoring design because it keeps scores and explanations consistent. I revised the suggestion to delete the original `src.main`: it remains useful as a baseline and is still covered by tests. I rejected treating the deterministic guardrail as an autonomous agent or fine-tuned model. More detail is in [ai_interactions.md](ai_interactions.md) and [model_card.md](model_card.md).

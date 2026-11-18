# Model Card: VibeFinder Project 4

## System summary

VibeFinder is an educational content-based recommender. It does not train a ranking model. It combines Gemini structured preference extraction, TF-IDF candidate retrieval, deterministic feature scoring, and reliability checks.

## Intended use

Use it to demonstrate an end-to-end Applied AI system: natural-language input, specialized structured prompting, retrieval, explainable ranking, guardrails, and a browser interface.

Do not use it as a production streaming service, a factual measure of musical quality, a child-safety classifier, or a replacement for listener feedback.

## Data

- Source: Free Music Archive metadata, normalized into `data/songs_fma.csv`.
- Current catalog: 5,000 tracks.
- Fields: title, artist, genre, tags, energy, tempo, valence, danceability, acousticness, duration, release year, source, and license.
- The source is a research/Creative Commons catalog, not a Spotify US-UK catalog.
- Some features are missing and some metadata is weak. The pipeline preserves missing values instead of pretending they are measured.

## Model and algorithm

### Gemini specialization

The parser is specialized with an English instruction, bounded enums, numeric limits, and JSON schema output. It returns a preference object rather than prose or invented track IDs. This makes the output easy to validate and pass to deterministic Python code.

### Retrieval

TF-IDF indexes title, artist, genre, tags, and derived mood. Cosine similarity returns the top positive candidates. `retrieval_query` and `keywords` expand the user's wording before retrieval.

### Ranking

The deterministic scorer rewards exact categorical matches and numeric closeness. The default genre-first weights are:

```text
genre 2.0, mood 1.0, energy 1.0, tempo 1.0,
other optional numeric features 0.5
```

Missing features contribute zero. An artist repetition penalty improves variety but may lower preference fit.

## Specialization comparison

| Input behavior | Unconstrained baseline | VibeFinder specialized parser |
| --- | --- | --- |
| `calm acoustic folk music for studying` | May return prose or arbitrary recommendations | Returns validated genre/mood/energy, numeric targets, keywords, and retrieval query |
| Invalid energy such as `2.0` | Could be accepted as text | Rejected by `validate_preferences()` because energy must be 0–1 |
| Final track choice | Model could invent a track | Only catalog tracks returned by TF-IDF and Python ranking can appear |

The specialization is constrained output behavior, not fine-tuning. It is measured by schema validation, range validation, and the FMA evaluation harness.

## Reliability and evaluation

The baseline evaluator passes 13/13 cases. The FMA harness evaluates three predefined prompts and currently passes 3/3, with at least 4/5 expected-genre hits per case and no blocked spoken-word titles. Pytest covers validation, scoring arithmetic, retrieval, filtering, deterministic order, and output guardrails.

These are regression checks, not a held-out human preference study. A passing score means the implementation follows its rules; it does not prove that listeners will enjoy every result.

## Limitations and risks

- TF-IDF is vocabulary-based and may miss synonyms.
- Gemini's numeric targets are language-based estimates, not audio measurements.
- FMA has missing features, uneven genre coverage, and occasional weak titles.
- Derived mood is a transparent heuristic from energy/valence, not a human annotation.
- Artist penalty improves local variety but does not guarantee fairness.
- No listening history, skip data, or personalization feedback is used.
- No audio preview is enabled until verified, licensed `audio_url` data is added.

## Reflection on AI collaboration

AI assistance was used for repository inspection, FMA normalization, retrieval design, test generation, Windows debugging, Gemini prompt design, UI design, and documentation. I accepted the recommendation to keep one shared scorer because it keeps scores and explanations consistent. I revised the suggestion to delete `src.main`: it remains a useful baseline and preserves regression coverage. I rejected describing the deterministic validator as an autonomous agent or fine-tuned model because the implementation does not plan with tools or update model weights.

## Bias and testing reflection

The system can reproduce metadata bias: FMA genre coverage is uneven, English-language examples are overrepresented, and exact labels treat related genres as different. Gemini can also infer subjective numeric targets from wording. The artist penalty improves local variety but does not guarantee demographic or cultural fairness. These limitations are documented rather than hidden.

Testing checks implementation reliability, not musical enjoyment. The current results are:

```text
pytest: 70 passed
baseline evaluator: 13/13 passed
FMA evaluator: 3/3 passed
```

The tests cover range validation, malformed catalogs, duplicate IDs, score arithmetic, deterministic ordering, blocked FMA records, fabricated explanations, constraints, and three FMA retrieval cases. The evaluation does not replace held-out listener ratings; future work should collect human relevance judgments and measure both ranking quality and exposure diversity.

## Future improvements

Add verified previews, multi-label genre/mood support, embedding retrieval, listener ratings, learned weights, balanced catalog coverage, and a held-out evaluation set with human relevance judgments.

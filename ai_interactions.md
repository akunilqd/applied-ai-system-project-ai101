# AI Collaboration and System Design Reflection

## How AI was used

AI assistance was used to:

- inspect the starter recommender and its tests;
- diagnose the FMA archive and normalize metadata;
- design and implement TF-IDF retrieval;
- explain and test the scoring formula;
- add Gemini structured preference extraction;
- debug Windows pytest temporary-directory permissions;
- design the browser interface and local API server;
- write regression, evaluation, and documentation files.

All generated code was run locally and checked against the actual repository behavior.

## Suggestions accepted

1. Keep one shared deterministic scorer for both the original and extended interfaces. This prevents scores and explanations from drifting apart.
2. Use structured Gemini output rather than free-form prose. The schema makes genre, mood, energy, and retrieval fields validateable.
3. Use a custom TF-IDF document made from title, artist, genre, tags, and mood. This is simple enough for a final project and transparent enough to explain.
4. Add a guardrail after ranking so the live web path checks catalog membership, score arithmetic, ordering, and explanations.

## Suggestions revised or rejected

1. The original suggestion to remove `src.main` was revised. It remains as a baseline CLI and supports regression tests.
2. A vector database was not added. The catalog is 5,000 rows and a sparse in-memory TF-IDF matrix is sufficient for this scope.
3. The deterministic reliability pipeline is not described as an autonomous agent or fine-tuned model. It validates and checks results but does not plan with tools.
4. Audio URLs were not fabricated. The UI includes a player shell, but playback waits for a verified, licensed preview field.

## Design decisions

The final architecture separates responsibilities: Gemini understands language, TF-IDF retrieves, Python scores, and guardrails verify. This limits the damage of a malformed model response and makes each stage testable. The web server keeps the API key server-side.

## Limitations and future work

The main limitation is metadata quality. FMA is useful for a demonstrator but does not provide the breadth or verified listening behavior of a commercial catalog. Future work should add human relevance labels, evaluate held-out prompts, learn weights from feedback, support semantic embeddings, and attach verified audio previews.

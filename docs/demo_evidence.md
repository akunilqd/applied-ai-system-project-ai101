# Reproducible Demo Evidence

These are captured interaction logs for the end-to-end VibeFinder workflow. The web request flows through Gemini parsing, expanded TF-IDF retrieval, deterministic scoring, and the output guardrail.

## Run the web demo

```powershell
.\.venv\Scripts\python.exe -m web.server
# Open http://127.0.0.1:8000
```

## Interaction 1 — calm acoustic study music

```text
Input: calm acoustic folk music for studying
Parsed preferences:
{'genre': 'folk', 'mood': 'calm', 'energy': 0.3, 'acousticness': 0.9}
Retrieval query:
calm acoustic folk music for studying and concentration

Top results:
Finale / folk
Heart On Fire / folk
Music of The Ages / folk
```

## Interaction 2 — energetic electronic workout

```text
Input: energetic electronic music for workout
Parsed preferences:
{'genre': 'electronic', 'mood': 'intense', 'energy': 0.9}
Keywords:
['electronic', 'workout', 'energetic', 'upbeat', 'gym', 'dance']

Top result:
02 opendoor.mp3 / electronic / score 3.973
Reason:
genre match (+2.000); energy 0.87344 vs 0.9 (+0.973); mood match (+1.000)
```

## Interaction 3 — sad relaxing folk music

```text
Input: sad relaxing folk music
Parsed preferences:
{'genre': 'folk', 'mood': 'sad', 'energy': 0.3,
 'valence': 0.2, 'acousticness': 0.8}

Top results:
Make It Last / folk
Forever / folk
Kokopelli / folk
```

## Guardrail behavior

```text
Input: genre=unknown, mood=sad, energy=0.2
Behavior: unknown genre is treated as unspecified.
Result: no false genre-match points are added.

Input: energy=1.5
Behavior: rejected before ranking.
Result: ValueError: energy must be between 0 and 1

Input: FMA title contains "Interview"
Behavior: removed during prepare_fma.py filtering.
Result: it cannot enter the retrieval catalog.
```

## Automated evidence

```text
pytest: 70 passed
baseline evaluator: 13/13 passed
FMA evaluator: 3/3 passed
```

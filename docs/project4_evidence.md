# Project 4 Rubric Evidence

This file maps the implemented project to the required rubric. It is evidence, not a claim that a grader must award a particular score.

## Required 21 points

| Rubric area | Evidence in this repository |
| --- | --- |
| Base project and original scope | README Section 1; `src/main.py`; original 24-track `data/songs.csv` baseline |
| Substantial AI feature | `src/query_parser.py` structured Gemini parser; `src/rag.py` TF-IDF/cosine retrieval; `scripts/prepare_fma.py` FMA catalog; live web path in `web/server.py` |
| Architecture diagram | `docs/architecture.mmd` shows browser input, Gemini, validation, TF-IDF, ranking, guardrail, and output |
| End-to-end demonstration | `web/server.py` + `web/index.html`; README setup/run commands; `test.py` live Gemini smoke test |
| Reliability | `src/recommender.py` validation; `src/reliability.py` output guardrail; FMA blocked-content filter; `scripts/evaluate_fma.py` |
| Documentation | `README.md`, `docs/system_design.md`, `model_card.md`, and this evidence file |
| AI collaboration/reflection | `ai_interactions.md` records accepted and revised/rejected suggestions, limits, and future work |

## End-to-end examples

### Example A — calm study music

Input:

```text
calm acoustic folk music for studying
```

Gemini produced structured fields similar to:

```python
genre=folk, mood=calm, energy=0.3,
acousticness=0.9,
keywords=[calm, acoustic, folk, study, concentration]
```

The final ranker returned folk tracks with reasons such as genre match, mood match, energy closeness, and acousticness closeness.

### Example B — energetic electronic workout

Input:

```text
energetic electronic music for working out
```

Observed parser output:

```python
genre=electronic, mood=intense, energy=0.9
keywords=[electronic, workout, energetic, upbeat, gym, dance]
```

Observed top result:

```text
02 opendoor.mp3 / electronic
genre match (+2.000); energy 0.87344 vs 0.9 (+0.973); mood match (+1.000)
```

### Example C — uncertain genre

Input:

```text
melancholy piano instrumental music
```

Gemini returned `genre=unknown`, low energy, low valence, low danceability, and high acousticness. The scorer treats `unknown` as unspecified rather than awarding a false genre match. This guardrail was added after observing that `unknown == unknown` could otherwise award genre points.

## Reliability demonstrations

| Input or fault | Expected behavior |
| --- | --- |
| Energy `1.5` | Reject with a range error |
| Misspelled preference `energi` | Reject as an unknown field |
| Duplicate/foreign output track | Reject through output guardrail |
| Fabricated explanation | Reject because it does not match score contributions |
| `--max-duration 1` | Return zero results with a constraint-preserved notice |
| FMA title containing `Interview` or `Podcast` | Remove during catalog preparation |
| Gemini returns `genre=unknown` | Do not award genre match points |

## Evaluation commands and evidence

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.evaluate --report docs/evaluation.json
.\.venv\Scripts\python.exe scripts/evaluate_fma.py --report docs/fma_evaluation.json
```

Current local results:

```text
pytest: 70 passed
baseline evaluator: 13/13 passed
FMA evaluator: 3/3 passed
```

## Stretch evidence

### RAG enhancement (+2 candidate)

`src.rag.py` uses a custom multi-field index over title, artist, genre, tags, and derived mood. `scripts/prepare_fma.py` adds the FMA source catalog and blocks spoken-word records before indexing. This is documented in `README.md` and `docs/system_design.md`. The offline FMA harness measures the result with three prompts and genre hit rate.

### Test harness (+2 candidate)

The original `src.evaluate` harness runs 13 fixed behavioral and guardrail cases. The new `scripts/evaluate_fma.py` runs three FMA retrieval cases and prints a pass/fail summary, with a committed report in `docs/fma_evaluation.json`.

### Specialization behavior (+2 candidate)

The Gemini parser uses constrained enums, bounded numeric fields, a structured JSON schema, and a domain-specific extraction prompt. `model_card.md` documents the difference between unconstrained prose and the validated structured behavior. This is specialization by constrained prompting, not fine-tuning.

### Not claimed

No agentic tool-planning workflow or fine-tuned model is claimed. The project deliberately keeps Gemini as a parser and Python as the deterministic source of truth.

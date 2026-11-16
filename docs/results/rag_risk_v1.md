# RAG + LLM scorer: results (rag_risk_v1.0)

Model: `qwen2.5:7b` via Ollama, temperature 0. Knowledge base: 54 sections from 15 tomato documents, each citing extension-service or FAO sources (`crops/tomato/knowledge/`).

Data: external dataset supplied for this project; not collected with this project's sensor node, 840 observations of 30 plants. The scorer is not trained on it; it sees each observation's sensor readings (current values and the last three readings of humidity) and growth stage. The dataset has no photos, so the photo input is empty.

## Grounding

- Answers that passed every check: **100.0%** (837 of 837); 26 needed one retry; 0 were rejected and given no score.
- Checks: quoted readings equal the real ones; every cited passage was actually retrieved; numbers in reasons come from the readings or the cited passage; only known disease ids.
- Most common rejection reasons: none.

## Task 1: is the plant diseased now?

837 of 837 observations had a grounded RAG score (168 positive).

| Scorer | ROC-AUC (95% CI) | PR-AUC (95% CI) | Brier |
|---|---:|---:|---:|
| Sensor model (out-of-fold) | 0.612 (0.491–0.744) | 0.264 (0.134–0.435) | 0.198 |
| RAG + LLM | 0.49 (0.404–0.577) | 0.2 (0.093–0.336) | 0.233 |
| Sensor + RAG fused (fixed weights) | 0.58 (0.516–0.658) | 0.23 (0.11–0.381) | 0.197 |

## Task 2: will a healthy plant become diseased within 7 days?

533 of 533 observations had a grounded RAG score (60 positive).

| Scorer | ROC-AUC (95% CI) | PR-AUC (95% CI) | Brier |
|---|---:|---:|---:|
| Sensor model (out-of-fold) | 0.549 (0.392–0.683) | 0.142 (0.061–0.308) | 0.229 |
| RAG + LLM | 0.458 (0.369–0.537) | 0.105 (0.047–0.19) | 0.239 |
| Sensor + RAG fused (fixed weights) | 0.52 (0.348–0.663) | 0.134 (0.058–0.273) | 0.207 |

## How to read this

- The RAG scorer encodes published agronomic rules (for example humidity above 85% favours leaf mold), so it shows whether textbook disease conditions line up with what happened to these plants.
- Fused scores use the fixed weights in `ml/fusion.py`, renormalised over the two scorers present; they were not tuned on this data, so the comparison is fair but not optimised.
- Plant-level intervals are wide with 30 plants; an interval that includes 0.5 means no reliable signal.

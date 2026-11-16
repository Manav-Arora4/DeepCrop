"""
Weighted fusion of the three disease scorers into one tomato disease-risk score.

  photo   P(diseased) from the leaf-photo model (tomato_cv_v2.0): 1 - P(healthy)
  sensor  P(risk) from the sensor-only model (sensor_risk_v1.0)
  rag     a 0-1 risk assessment from the RAG + LLM advisor, grounded in retrieved
          knowledge and the plant's actual readings (Phase 8; interface defined here)

Each scorer is built and evaluated on its own; this module only combines their outputs.
A missing scorer (no photo yet, no reading, LLM offline) is left out and the remaining
weights are renormalised, so the result always says which scorers it used.

The default weights are provisional. They should be fitted on held-out observations that
have a photo, a sensor reading and a known outcome for the same plant and time; until then,
report fused scores as using provisional weights.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

# Provisional: photo is the only scorer with a validated real-world result so far
# (63.3% accuracy on PlantDoc); the sensor scorer showed weak signal (ROC-AUC 0.55-0.61).
DEFAULT_WEIGHTS = {"photo": 0.5, "sensor": 0.25, "rag": 0.25}


def risk_level(score: float) -> str:
    """Same cut-offs as score_to_risk_level in ml/disease_risk/models/random_forest.py."""
    if score < 0.25:
        return "low"
    if score < 0.50:
        return "moderate"
    if score < 0.75:
        return "high"
    return "critical"


@dataclass
class FusedRisk:
    score: float
    level: str
    contributions: Dict[str, float]   # weighted share of each scorer used
    used: Dict[str, float]            # raw score from each scorer used
    weights: Dict[str, float]         # renormalised weights actually applied
    provisional_weights: bool = True
    missing: list = field(default_factory=list)


def photo_score(class_probabilities: Dict[str, float]) -> float:
    """P(diseased) from the CV model's class probabilities."""
    return 1.0 - float(class_probabilities.get("tomato_healthy", 0.0))


def fuse(
    photo: Optional[float] = None,
    sensor: Optional[float] = None,
    rag: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    provisional_weights: bool = True,
) -> FusedRisk:
    """Combine the available 0-1 scores with weights renormalised over the scorers present."""
    weights = weights or DEFAULT_WEIGHTS
    scores = {"photo": photo, "sensor": sensor, "rag": rag}
    used = {k: float(v) for k, v in scores.items() if v is not None}
    if not used:
        raise ValueError("At least one scorer must provide a score.")
    for k, v in used.items():
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{k} score must be between 0 and 1, got {v}")

    total = sum(weights[k] for k in used)
    applied = {k: weights[k] / total for k in used}
    contributions = {k: round(applied[k] * used[k], 4) for k in used}
    score = round(sum(contributions.values()), 4)
    return FusedRisk(
        score=score,
        level=risk_level(score),
        contributions=contributions,
        used=used,
        weights={k: round(w, 4) for k, w in applied.items()},
        provisional_weights=provisional_weights,
        missing=[k for k, v in scores.items() if v is None],
    )

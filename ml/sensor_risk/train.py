"""
Train and evaluate the sensor-only scorer (one of the three models in the weighted fusion).

Two tasks, reported separately (see docs/DATA_COLLECTION.md):
  detection   is the plant diseased now?
  risk_7d     will a currently healthy plant be observed diseased within 7 days?

Evaluation is grouped cross-validation by plant: each fold holds out whole plants, so the model
is always scored on plants it never saw. Each model is compared with a no-skill baseline
(always predict the training prevalence), with 95% bootstrap intervals over plants.

Run:  python -m ml.sensor_risk.train --source "external dataset supplied for this project"
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.sensor_risk.features import FEATURES, build_features, detection_set, load_observations, risk_set

OUT_DIR = Path("crops/tomato/models/sensor_risk")
REPORT = Path("docs/results/sensor_risk_v1.md")
SEED = 42


def candidates():
    return {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
        "random_forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=3, class_weight="balanced",
                                                random_state=SEED, n_jobs=-1),
    }


def grouped_oof(model_fn, X, y, groups, folds=5):
    """Out-of-fold probabilities with whole plants held out per fold."""
    oof = np.full(len(y), np.nan)
    prior = np.full(len(y), np.nan)
    cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=SEED)
    for tr, te in cv.split(X, y, groups):
        m = model_fn()
        m.fit(X.iloc[tr], y.iloc[tr])
        oof[te] = m.predict_proba(X.iloc[te])[:, 1]
        prior[te] = y.iloc[tr].mean()
    return oof, prior


def metrics(y, p):
    if len(set(y)) < 2:
        return {"roc_auc": None, "pr_auc": None, "f1": None, "brier": None}
    return {
        "roc_auc": round(float(roc_auc_score(y, p)), 3),
        "pr_auc": round(float(average_precision_score(y, p)), 3),
        "f1": round(float(f1_score(y, (p >= 0.5).astype(int), zero_division=0)), 3),
        "brier": round(float(brier_score_loss(y, p)), 3),
    }


def plant_bootstrap(y, p, groups, n=1000):
    """95% interval for ROC-AUC and PR-AUC, resampling whole plants."""
    rng = np.random.default_rng(SEED)
    plants = np.unique(groups)
    idx_by_plant = {g: np.where(groups == g)[0] for g in plants}
    aucs, aps = [], []
    for _ in range(n):
        idx = np.concatenate([idx_by_plant[g] for g in rng.choice(plants, len(plants), replace=True)])
        if len(set(y[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y[idx], p[idx]))
        aps.append(average_precision_score(y[idx], p[idx]))
    ci = lambda v: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]
    return {"roc_auc_ci95": ci(aucs), "pr_auc_ci95": ci(aps)}


def run_task(name, data, y):
    X, groups = data[FEATURES], data["plant_id"].to_numpy()
    result = {
        "rows": int(len(y)), "positives": int(y.sum()), "plants": int(len(set(groups))),
        "positive_plants": int(data.loc[y.to_numpy() == 1, "plant_id"].nunique()), "models": {},
    }
    best_name, best_auc = None, -1.0
    for mname, ctor in candidates().items():
        oof, prior = grouped_oof(lambda c=ctor: candidates()[mname], X, y, groups)
        m = metrics(y.to_numpy(), oof) | plant_bootstrap(y.to_numpy(), oof, groups)
        result["models"][mname] = m
        if m["roc_auc"] is not None and m["roc_auc"] > best_auc:
            best_name, best_auc = mname, m["roc_auc"]
    result["models"]["no_skill_baseline"] = metrics(y.to_numpy(), prior)
    result["best"] = best_name

    final = candidates()[best_name].fit(X, y)
    if best_name == "random_forest":
        imp = final.feature_importances_
    else:
        imp = np.abs(final[-1].coef_[0])
        imp = imp / imp.sum()
    result["feature_importance"] = dict(sorted(((f, round(float(v), 3)) for f, v in zip(FEATURES, imp)),
                                               key=lambda kv: -kv[1]))
    print(f"[sensor_risk] {name}: {result['rows']} rows, {result['positives']} positive "
          f"({result['positive_plants']} plants) -> best {best_name} ROC-AUC {best_auc:.3f}")
    return result, final


def write_report(card):
    names = {"logistic_regression": "Logistic regression", "random_forest": "Random forest", "no_skill_baseline": "No-skill baseline"}
    lines = [
        "# Sensor-only scorer: results (sensor_risk_v1.0)",
        "",
        f"Data: {card['data']['source']}. {card['data']['rows']} observations of {card['data']['plants']} tomato plants "
        f"({card['data']['date_range']}); device ID as recorded in the dataset: `{', '.join(card['data']['devices'])}`. "
        "pH is from an uncalibrated probe and is used only as a change from each plant's own baseline.",
        "",
        "Evaluation: 5-fold cross-validation grouped by plant (every score comes from plants the model never saw), "
        "95% intervals from 1,000 plant-level bootstrap resamples. Columns that would leak the answer "
        "(treatment, notes, severity, leaf counts) are never used as features.",
        "",
    ]
    for task, title in [("detection", "Task 1: is the plant diseased now?"), ("risk_7d", "Task 2: will a healthy plant become diseased within 7 days?")]:
        t = card["tasks"][task]
        lines += [f"## {title}", "",
                  f"{t['rows']} observations, {t['positives']} positive, from {t['positive_plants']} of {t['plants']} plants.", "",
                  "| Model | ROC-AUC (95% CI) | PR-AUC (95% CI) | F1 @0.5 | Brier |", "|---|---:|---:|---:|---:|"]
        for mname, m in t["models"].items():
            roc = f"{m['roc_auc']}" + (f" ({m['roc_auc_ci95'][0]}–{m['roc_auc_ci95'][1]})" if "roc_auc_ci95" in m else "")
            pr = f"{m['pr_auc']}" + (f" ({m['pr_auc_ci95'][0]}–{m['pr_auc_ci95'][1]})" if "pr_auc_ci95" in m else "")
            best = " **(selected)**" if mname == t["best"] else ""
            lines.append(f"| {names[mname]}{best} | {roc} | {pr} | {m['f1']} | {m['brier']} |")
        top = list(t["feature_importance"].items())[:5]
        lines += ["", "Most influential features: " + ", ".join(f"`{f}` ({v})" for f, v in top) + ".", ""]
    lines += [
        "## Limits",
        "",
        f"- Few independent units: {card['data']['plants']} plants. Plant-level intervals are wide by design; read them, not just the point estimate.",
        f"- Task 2 rests on {card['tasks']['risk_7d']['positive_plants']} plants that became diseased during collection.",
        "- The selected model is the better of two candidates on the same cross-validation, so its score is slightly optimistic.",
        "- When an interval includes 0.5, the sensors show no reliable signal for that task on this data. Report that as a finding, not a failure.",
        "- These are sensor-only scores. They become one input to the weighted fusion with the photo model and the RAG assessment (see `ml/fusion.py`).",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Train the sensor-only tomato disease scorer")
    parser.add_argument("--source", required=True, help='Where the data came from, e.g. "external dataset supplied for this project"')
    args = parser.parse_args()

    df = build_features(load_observations())
    tasks, models = {}, {}
    for task, (data, y) in {"detection": detection_set(df), "risk_7d": risk_set(df, 7)}.items():
        tasks[task], models[task] = run_task(task, data, y)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for task, model in models.items():
        joblib.dump(model, OUT_DIR / f"sensor_{task}_v1.joblib")
    card = {
        "version": "sensor_risk_v1.0",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": FEATURES,
        "data": {
            "source": args.source,
            "file": "data/user_collected/tomato/observations.csv",
            "rows": int(len(df)), "plants": int(df["plant_id"].nunique()),
            "date_range": f"{df['ts'].min().date()} to {df['ts'].max().date()}",
            "devices": sorted(df["sensor_device_id"].dropna().unique().tolist()),
        },
        "evaluation": "5-fold StratifiedGroupKFold by plant_id, seed 42; plant-level bootstrap CIs",
        "tasks": tasks,
        "weights_files": {t: f"sensor_{t}_v1.joblib" for t in models},
    }
    (OUT_DIR / "model_card_v1.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    write_report(card)
    print(f"[sensor_risk] Wrote {OUT_DIR} and {REPORT}")


if __name__ == "__main__":
    main()

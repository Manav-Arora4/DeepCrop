"""
Evaluate the RAG + LLM scorer on the observation dataset and compare it with the sensor scorer.

The RAG scorer is not trained on this data: it reads each observation's conditions and the
knowledge base, so every observation is a fair test. It sees the same sensor readings as the
sensor scorer (the dataset has no photos). Reported for both tasks:

  - grounding: share of answers that passed every check, and how many needed a retry
  - ROC-AUC / PR-AUC with plant-level bootstrap intervals, for
      sensor scorer (grouped out-of-fold probabilities), RAG scorer, and sensor+RAG fused
      with fixed a-priori weights from ml/fusion.py (not fitted on this data)

Run:  python -m ml.rag_risk.evaluate            (takes ~1 h on an RTX 4060 with qwen2.5:7b)
      python -m ml.rag_risk.evaluate --limit 40  (quick check)
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from ml.fusion import fuse
from ml.rag_risk.scorer import READING_KEYS, score
from ml.sensor_risk.features import FEATURES, build_features, detection_set, load_observations, risk_set
from ml.sensor_risk.train import candidates, grouped_oof, metrics, plant_bootstrap

CACHE = Path("data/processed/tomato/rag_risk_scores.jsonl")
REPORT = Path("docs/results/rag_risk_v1.md")


async def score_all(df: pd.DataFrame, model: str, limit: int | None) -> dict:
    done = {}
    if CACHE.exists():
        for line in CACHE.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done[r["observation_id"]] = r
    todo = [row for _, row in df.iterrows() if row["observation_id"] not in done]
    if limit:
        todo = todo[: max(0, limit - len(done))]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    async with httpx.AsyncClient() as client:
        with CACHE.open("a", encoding="utf-8") as f:
            for i, row in enumerate(todo, 1):
                readings = {k: row[k] for k in READING_KEYS}
                r = await score(readings, row["growth_stage"], model=model, client=client)
                rec = {"observation_id": row["observation_id"], "score": r.score, "grounded": r.grounded,
                       "attempts": r.attempts, "failures": r.failures, "likely_diseases": r.likely_diseases}
                f.write(json.dumps(rec) + "\n")
                f.flush()
                done[row["observation_id"]] = rec
                if i % 25 == 0:
                    rate = (time.time() - t0) / i
                    print(f"[rag_risk] {i}/{len(todo)} scored, {rate:.1f}s each, ~{rate * (len(todo) - i) / 60:.0f} min left", flush=True)
    return done


def compare(name, data, y, rag_scores, sensor_oof):
    groups = data["plant_id"].to_numpy()
    rag = data["observation_id"].map(lambda o: rag_scores.get(o, {}).get("score")).to_numpy(dtype=float)
    ok = ~np.isnan(rag)
    y_ok, g_ok = y.to_numpy()[ok], groups[ok]
    sens = sensor_oof[ok]
    fused = np.array([fuse(sensor=s, rag=r).score for s, r in zip(sens, rag[ok])])
    out = {"rows_scored": int(ok.sum()), "rows_total": int(len(y)), "positives": int(y_ok.sum())}
    for label, p in [("sensor", sens), ("rag", rag[ok]), ("sensor_plus_rag", fused)]:
        out[label] = metrics(y_ok, p) | plant_bootstrap(y_ok, p, g_ok)
    return out


def write_report(summary):
    lines = [
        "# RAG + LLM scorer: results (rag_risk_v1.0)",
        "",
        f"Model: `{summary['llm']}` via Ollama, temperature 0. Knowledge base: {summary['chunks']} sections from "
        "15 tomato documents, each citing extension-service or FAO sources (`crops/tomato/knowledge/`).",
        "",
        f"Data: {summary['source']}, {summary['rows']} observations of {summary['plants']} plants. The scorer is not trained on it; "
        "it sees each observation's sensor readings (current values and the last three readings of humidity) and growth stage. "
        "The dataset has no photos, so the photo input is empty.",
        "",
        "## Grounding",
        "",
        f"- Answers that passed every check: **{summary['grounding']['pass_rate']:.1%}** "
        f"({summary['grounding']['passed']} of {summary['grounding']['total']}); "
        f"{summary['grounding']['needed_retry']} needed one retry; {summary['grounding']['failed']} were rejected and given no score.",
        "- Checks: quoted readings equal the real ones; every cited passage was actually retrieved; numbers in reasons come from the "
        "readings or the cited passage; only known disease ids.",
        f"- Most common rejection reasons: {summary['grounding']['top_failures'] or 'none'}.",
        "",
    ]
    for task, title in [("detection", "Task 1: is the plant diseased now?"), ("risk_7d", "Task 2: will a healthy plant become diseased within 7 days?")]:
        t = summary["tasks"][task]
        lines += [f"## {title}", "", f"{t['rows_scored']} of {t['rows_total']} observations had a grounded RAG score ({t['positives']} positive).", "",
                  "| Scorer | ROC-AUC (95% CI) | PR-AUC (95% CI) | Brier |", "|---|---:|---:|---:|"]
        for key, label in [("sensor", "Sensor model (out-of-fold)"), ("rag", "RAG + LLM"), ("sensor_plus_rag", "Sensor + RAG fused (fixed weights)")]:
            m = t[key]
            lines.append(f"| {label} | {m['roc_auc']} ({m['roc_auc_ci95'][0]}–{m['roc_auc_ci95'][1]}) | "
                         f"{m['pr_auc']} ({m['pr_auc_ci95'][0]}–{m['pr_auc_ci95'][1]}) | {m['brier']} |")
        lines.append("")
    lines += [
        "## How to read this",
        "",
        "- The RAG scorer encodes published agronomic rules (for example humidity above 85% favours leaf mold), so it shows whether "
        "textbook disease conditions line up with what happened to these plants.",
        "- Fused scores use the fixed weights in `ml/fusion.py`, renormalised over the two scorers present; they were not tuned on "
        "this data, so the comparison is fair but not optimised.",
        "- Plant-level intervals are wide with 30 plants; an interval that includes 0.5 means no reliable signal.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--source", default="external dataset supplied for this project; not collected with this project's sensor node")
    args = ap.parse_args()

    from backend.services.rag_service import get_rag_service
    chunks = asyncio.run(get_rag_service().ingest_crop_knowledge("tomato", Path("crops/tomato/knowledge")))

    df = build_features(load_observations())
    scored = asyncio.run(score_all(df[df["disease_status"].isin(["healthy", "diseased"])], args.model, args.limit))
    if args.limit:
        print(f"[rag_risk] Quick run: {len(scored)} observations cached in {CACHE}; rerun without --limit for the full evaluation.")
        return

    tasks = {}
    for task, (data, y) in {"detection": detection_set(df), "risk_7d": risk_set(df, 7)}.items():
        best = json.loads(Path("crops/tomato/models/sensor_risk/model_card_v1.json").read_text())["tasks"][task]["best"]
        oof, _ = grouped_oof(lambda: candidates()[best], data[FEATURES], y, data["plant_id"].to_numpy())
        tasks[task] = compare(task, data, y, scored, oof)

    recs = list(scored.values())
    fails = pd.Series([f.split(" ")[0:3] and " ".join(f.split(" ")[:4]) for r in recs if not r["grounded"] for f in r["failures"]])
    summary = {
        "llm": args.model, "chunks": chunks, "source": args.source,
        "rows": int(len(df)), "plants": int(df["plant_id"].nunique()),
        "grounding": {
            "total": len(recs), "passed": sum(r["grounded"] for r in recs),
            "pass_rate": sum(r["grounded"] for r in recs) / len(recs),
            "needed_retry": sum(r["grounded"] and r["attempts"] == 2 for r in recs),
            "failed": sum(not r["grounded"] for r in recs),
            "top_failures": "; ".join(f"{k} ({v})" for k, v in fails.value_counts().head(3).items()),
        },
        "tasks": tasks,
    }
    Path("crops/tomato/models/rag_risk").mkdir(parents=True, exist_ok=True)
    Path("crops/tomato/models/rag_risk/model_card_v1.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(summary)
    print(json.dumps({t: {k: v.get("roc_auc") if isinstance(v, dict) else v for k, v in m.items()} for t, m in tasks.items()}, indent=2))


if __name__ == "__main__":
    main()

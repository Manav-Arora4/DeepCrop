"""
Live progress for the RAG scorer evaluation (python -m ml.rag_risk.evaluate).

Reads the evaluation's cache file every few seconds and shows how many observations are scored,
the grounding pass rate so far, the current speed and the time left. Safe to run alongside the
evaluation; it only reads. Ctrl+C to stop watching (the evaluation keeps running).

Run:  .venv/Scripts/python -m ml.rag_risk.progress
"""

import json
import time
from collections import deque
from pathlib import Path

CACHE = Path("data/processed/tomato/rag_risk_scores.jsonl")
TOTAL = 837  # observations labelled healthy or diseased (unsure rows excluded)
WIDTH = 24


def read():
    if not CACHE.exists():
        return []
    rows = []
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # a line being written right now
    return rows


def main(interval: float = 5.0):
    history = deque(maxlen=60)  # (time, count) samples for the speed estimate
    print("RAG scorer evaluation progress (Ctrl+C stops watching, not the evaluation)\n")
    while True:
        rows = read()
        n = len(rows)
        now = time.time()
        history.append((now, n))
        grounded = sum(r.get("grounded") for r in rows)
        retried = sum(r.get("attempts") == 2 for r in rows)
        rate = None
        if len(history) >= 2 and history[-1][1] > history[0][1]:
            rate = (history[-1][0] - history[0][0]) / (history[-1][1] - history[0][1])
        filled = int(WIDTH * n / TOTAL)
        bar = "#" * filled + "-" * (WIDTH - filled)
        eta = f"~{rate * (TOTAL - n) / 60:.0f} min left" if rate else "measuring..."
        speed = f"{rate:.1f}s/obs" if rate else "-"
        # Short enough for a narrow panel, so \r redraws in place instead of wrapping
        line = f"\r[{bar}] {n}/{TOTAL} {n / TOTAL:.0%} | grounded {grounded / max(n, 1):.0%} | {speed} | {eta}"
        print(line.ljust(92), end="", flush=True)
        if n >= TOTAL:
            print("\n\nAll observations scored. The evaluation is now writing docs/results/rag_risk_v1.md.")
            return
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped watching. The evaluation is still running.")

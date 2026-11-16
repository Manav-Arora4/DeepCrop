"""
Retrieval test for the tomato knowledge base, run before any LLM is involved.

Each query has the document that should answer it. Reports hit@1, hit@3 and mean reciprocal
rank over documents (the best-ranked chunk of each document), and checks every result is
tagged with the tomato crop.

Run:  python -m ml.rag_risk.eval_retrieval          (re-ingests the knowledge base first)
"""

import asyncio
import json
from pathlib import Path

from backend.services.rag_service import get_rag_service

QUERIES = [
    ("brown spots with concentric rings like a target on older lower leaves", "diseases/early_blight"),
    ("dark greasy water-soaked patches spreading fast in cool wet weather, white growth under leaves", "diseases/late_blight"),
    ("many small circular spots with grey centres and dark borders on lower leaves", "diseases/septoria_leaf_spot"),
    ("small dark spots with yellow halo on leaves and raised scabby spots on fruit, bacteria", "diseases/bacterial_spot"),
    ("pale yellow patches on top of leaves with olive velvety mould underneath in a humid greenhouse", "diseases/leaf_mold"),
    ("Corynespora lesions on mature leaves, no resistant varieties available", "diseases/target_spot"),
    ("whiteflies, upward curling leaves with yellow margins and stunted plants", "diseases/yellow_leaf_curl"),
    ("light and dark green mottled mosaic leaves, virus spread by handling and tools", "diseases/mosaic_virus"),
    ("tiny stippling dots on leaves with fine webbing in hot dry weather", "diseases/spider_mites"),
    ("what does a healthy tomato leaf look like", "diseases/healthy"),
    ("dark sunken patch at the bottom of the fruit, calcium deficiency", "soil_nutrients"),
    ("what soil pH should tomatoes be grown at", "soil_nutrients"),
    ("should I add lime if the soil test pH is already fine", "soil_nutrients"),
    ("how much water does a tomato crop need over the season", "growth_stages_cultivation"),
    ("which growth stage is most sensitive to water shortage, flower drop", "growth_stages_cultivation"),
    ("crop coefficient Kc for tomato at mid season", "growth_stages_cultivation"),
    ("how to prevent fungal leaf disease by keeping leaves dry and improving airflow", "disease_prevention"),
    ("rotate fungicides by FRAC code to avoid resistance", "disease_prevention"),
    ("drip irrigation versus overhead sprinklers for tomatoes", "irrigation"),
    ("ideal temperature range for growing tomatoes", "general"),
]


async def main(k: int = 5):
    rag = get_rag_service()
    n = await rag.ingest_crop_knowledge("tomato", Path("crops/tomato/knowledge"), force=True)
    hits1 = hits3 = 0
    rr = []
    wrong_crop = 0
    rows = []
    for query, expected in QUERIES:
        res = await rag.retrieve("tomato", query, k=k)
        docs = []
        for r in res:
            wrong_crop += r["metadata"].get("crop") != "tomato"
            if r["source"] not in docs:
                docs.append(r["source"])
        rank = docs.index(expected) + 1 if expected in docs else None
        hits1 += rank == 1
        hits3 += rank is not None and rank <= 3
        rr.append(1 / rank if rank else 0.0)
        rows.append({"query": query, "expected": expected, "rank": rank, "top3": docs[:3]})
    summary = {
        "chunks_ingested": n, "queries": len(QUERIES), "k": k,
        "hit@1": round(hits1 / len(QUERIES), 3), "hit@3": round(hits3 / len(QUERIES), 3),
        "mrr": round(sum(rr) / len(rr), 3), "results_not_tagged_tomato": wrong_crop,
    }
    out = Path("docs/results/rag_retrieval_v1.json")
    out.write_text(json.dumps({"summary": summary, "queries": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in rows:
        if r["rank"] != 1:
            print(f"  rank {r['rank']}: {r['query'][:60]!r} expected {r['expected']}, got {r['top3']}")


if __name__ == "__main__":
    asyncio.run(main())

"""
RAG + LLM disease-risk scorer: the third scorer in the weighted fusion (ml/fusion.py).

Given one plant's current conditions (and, when available, the photo model's diagnosis), it
retrieves matching passages from the crop knowledge base and asks a local LLM (Ollama) for a
0-1 disease-risk score with cited evidence. Every answer is checked before it is used:

  - readings_cited: every number the model quotes must equal the reading it was given
  - reasons: any number in a reason must be a reading or appear in the passage it cites
  - evidence: every cited chunk_id must be one of the passages actually retrieved (at least one)
  - likely_diseases: only the crop's known disease ids
  - risk in [0, 1]; the level is recomputed from the score with the shared cut-offs

An answer that fails is retried once with the failure listed; if it fails again the scorer
returns no score (grounded=False), so the fusion leaves it out rather than using it.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from backend.services.rag_service import get_rag_service
from ml.fusion import risk_level

DISEASE_IDS = [
    "tomato_bacterial_spot", "tomato_early_blight", "tomato_late_blight", "tomato_leaf_mold",
    "tomato_septoria_leaf_spot", "tomato_spider_mites", "tomato_target_spot",
    "tomato_yellow_leaf_curl_virus", "tomato_mosaic_virus",
]

SYSTEM = """You assess tomato disease risk for one plant using ONLY the readings and knowledge passages provided.
Rules:
- Base every judgement on the passages. Cite the chunk_id of each passage you rely on.
- Never invent, round or change a reading. In "readings_cited" copy the exact values you used.
- Only name diseases from the allowed list. If conditions favour none, return an empty list.
- "risk" is the probability (0 to 1) that this plant has or will develop a disease within 7 days.
Return JSON only, with exactly these keys:
{"risk": number, "likely_diseases": [ids], "evidence": [{"chunk_id": string, "reason": string}], "readings_cited": {name: number}}"""

READING_KEYS = ["temperature_c", "humidity_pct", "soil_moisture_pct", "humidity_mean_3", "humidity_max_3", "hours_humid_proxy_3"]


@dataclass
class RagRisk:
    score: Optional[float]
    level: Optional[str]
    grounded: bool
    likely_diseases: List[str] = field(default_factory=list)
    evidence: List[Dict[str, str]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    attempts: int = 0
    model: str = ""


def build_query(readings: Dict[str, float], growth_stage: str, photo: Optional[Dict[str, Any]]) -> str:
    q = (f"tomato disease risk conditions: air temperature {readings['temperature_c']:.0f} C, relative humidity "
         f"{readings['humidity_pct']:.0f} percent, leaf wetness, soil moisture {readings['soil_moisture_pct']:.0f} percent, "
         f"{growth_stage} stage. Which diseases are favoured and how to prevent them.")
    if photo:
        q = f"{photo['disease']} symptoms and favourable conditions. " + q
    return q


NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def numbers_in(text: str) -> set:
    return {round(float(n), 1) for n in NUMBER.findall(text or "")}


def check(answer: Dict[str, Any], readings: Dict[str, float], chunk_ids: List[str],
          passage_text: Optional[Dict[str, str]] = None) -> List[str]:
    fails = []
    # Any number quoted in a reason must be a reading or appear in the passage it cites
    allowed = {round(v, 1) for v in readings.values()} | {round(v) * 1.0 for v in readings.values()}
    for e in answer.get("evidence") or []:
        if isinstance(e, dict) and passage_text and e.get("chunk_id") in passage_text:
            stray = numbers_in(e.get("reason", "")) - allowed - numbers_in(passage_text[e["chunk_id"]])
            if stray:
                fails.append(f"reason for {e['chunk_id']} quotes numbers {sorted(stray)} that are neither readings nor in that passage")
    risk = answer.get("risk")
    if not isinstance(risk, (int, float)) or not 0 <= risk <= 1:
        fails.append(f"risk must be a number between 0 and 1, got {risk!r}")
    ev = answer.get("evidence") or []
    if not ev:
        fails.append("no evidence cited")
    for e in ev:
        if not isinstance(e, dict) or e.get("chunk_id") not in chunk_ids:
            fails.append(f"cited chunk_id {e.get('chunk_id') if isinstance(e, dict) else e!r} was not among the passages provided")
    for d in answer.get("likely_diseases") or []:
        if d not in DISEASE_IDS:
            fails.append(f"unknown disease id {d!r}")
    for k, v in (answer.get("readings_cited") or {}).items():
        if k not in readings:
            fails.append(f"cited reading {k!r} was not provided")
        elif not isinstance(v, (int, float)) or abs(float(v) - readings[k]) > 0.05:
            fails.append(f"reading {k} cited as {v!r} but the actual value is {readings[k]}")
    return fails


async def ask(client: httpx.AsyncClient, model: str, base_url: str, prompt: str) -> Dict[str, Any]:
    r = await client.post(f"{base_url}/api/chat", json={
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0, "seed": 42, "num_ctx": 4096},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
    }, timeout=180)
    r.raise_for_status()
    text = r.json()["message"]["content"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}


async def score(
    readings: Dict[str, float],
    growth_stage: str,
    photo: Optional[Dict[str, Any]] = None,
    crop_id: str = "tomato",
    model: str = "qwen2.5:7b",
    base_url: str = "http://localhost:11434",
    k: int = 5,
    client: Optional[httpx.AsyncClient] = None,
) -> RagRisk:
    readings = {k_: round(float(v), 2) for k_, v in readings.items() if v is not None}
    passages = await get_rag_service().retrieve(crop_id, build_query(readings, growth_stage, photo), k=k)
    chunk_ids = [p["chunk_id"] for p in passages]
    context = "\n\n".join(f"[chunk_id: {p['chunk_id']}]\n{p['content']}" for p in passages)
    photo_text = (f"Leaf-photo model: {photo['disease']} ({photo['confidence']:.0%} confidence)." if photo
                  else "No leaf photo for this observation.")
    prompt = (f"Plant readings (exact values): {json.dumps(readings)}\nGrowth stage: {growth_stage}\n{photo_text}\n"
              f"Allowed disease ids: {DISEASE_IDS}\n\nKnowledge passages:\n{context}")

    own_client = client is None
    client = client or httpx.AsyncClient()
    result = RagRisk(score=None, level=None, grounded=False, model=model)
    try:
        answer, fails = {}, []
        for attempt in (1, 2):
            p = prompt if attempt == 1 else prompt + "\n\nYour previous answer failed these checks; fix them:\n- " + "\n- ".join(fails)
            try:
                answer = await ask(client, model, base_url, p)
                fails = check(answer, readings, chunk_ids, {p["chunk_id"]: p["content"] for p in passages})
            except Exception as e:
                fails = [f"LLM call failed: {e}"]
            result.attempts = attempt
            if not fails:
                break
        result.failures = fails
        if not fails:
            refs = {r for p in passages if p["chunk_id"] in {e["chunk_id"] for e in answer["evidence"]} for r in p["references"]}
            result.score = round(float(answer["risk"]), 3)
            result.level = risk_level(result.score)
            result.grounded = True
            result.likely_diseases = answer.get("likely_diseases") or []
            result.evidence = answer["evidence"]
            result.references = sorted(refs)
    finally:
        if own_client:
            await client.aclose()
    return result


if __name__ == "__main__":
    demo = {"temperature_c": 27.4, "humidity_pct": 91.0, "soil_moisture_pct": 72.0,
            "humidity_mean_3": 88.3, "humidity_max_3": 93.0, "hours_humid_proxy_3": 3.0}
    print(asyncio.run(score(demo, "flowering")))

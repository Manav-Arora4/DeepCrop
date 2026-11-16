"""
Draw the report's diagrams (architecture, use case, E-R, DFD, flowchart, hardware) as PNGs.

Run:  .venv/Scripts/python docs/report/build/diagrams.py   ->  docs/report/figures/*.png
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11})

INK, GREEN, MINT, GREY, AMBER = "#141814", "#13662F", "#DCF5E3", "#F1F3EE", "#FBEFD9"


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fill=GREY, edge=INK, size=10.5, bold_first=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fill, ec=edge, lw=1.1))
    lines = text.split("\n")
    n = len(lines)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h / 2 + (n - 1) * 1.6 - i * 3.2, line, ha="center", va="center",
                fontsize=size if i else size + 0.5, fontweight="bold" if (i == 0 and bold_first) else "normal", color=INK)


def arrow(ax, x1, y1, x2, y2, label="", style="-|>", rad=0.0, lw=1.1):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12, lw=lw, color=INK,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.6, label, ha="center", va="bottom", fontsize=9, color=GREEN, style="italic")


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def architecture():
    fig, ax = canvas(11.8, 7.4)
    box(ax, 2, 56, 24, 12, "ESP32-S3 field unit\nDHT22 · soil moisture · pH\nWi-Fi, JSON every 60 s", fill=MINT)
    box(ax, 2, 33, 24, 12, "Leaf photo\nphone camera upload", fill=MINT)
    box(ax, 38, 44, 26, 16, "FastAPI backend\nvalidation · crop modules\nREST API", fill=GREY)
    box(ax, 38, 22, 26, 10, "PostgreSQL\nreadings · predictions · advice")
    box(ax, 76, 60, 30, 11, "Photo scorer\nEfficientNet-B0 (tomato_cv_v2.0)", fill=AMBER)
    box(ax, 76, 45, 30, 11, "Sensor scorer\nlogistic regression (sensor_risk_v1.0)", fill=AMBER)
    box(ax, 76, 30, 30, 11, "RAG + LLM scorer\nChromaDB + bge-small + qwen2.5:7b", fill=AMBER)
    box(ax, 76, 10, 30, 13, "Weighted fusion\nrisk 0–100 · level\nper-scorer breakdown", fill=MINT)
    box(ax, 38, 2, 26, 12, "React dashboard\n3D field unit · charts\nadvisor with sources", fill=MINT)
    box(ax, 2, 10, 24, 12, "Knowledge base\n15 tomato documents\nextension + FAO sources")
    arrow(ax, 26, 62, 38, 54, "HTTP POST")
    arrow(ax, 26, 39, 38, 48, "upload")
    arrow(ax, 51, 44, 51, 32)
    arrow(ax, 64, 56, 76, 65)
    arrow(ax, 64, 52, 76, 50)
    arrow(ax, 64, 48, 76, 35)
    # Knowledge base feeds the RAG scorer along a lane between PostgreSQL and the dashboard
    ax.plot([26, 70], [17.5, 17.5], color=INK, lw=1.1)
    ax.text(48, 18.6, "retrieval", ha="center", va="bottom", fontsize=9, color=GREEN, style="italic")
    arrow(ax, 70, 17.5, 77, 30)
    # Each scorer feeds the fusion in parallel via a bus on the right
    for y in (65.5, 50.5, 35.5):
        ax.plot([106, 110], [y, y], color=INK, lw=1.1)
    ax.plot([110, 110], [65.5, 16.5], color=INK, lw=1.1)
    arrow(ax, 110, 16.5, 106.5, 16.5)
    ax.text(111, 41, "scores\n0–1", fontsize=9, color=GREEN, style="italic", va="center")
    arrow(ax, 76, 16, 64, 9)
    save(fig, "fig_architecture.png")


def use_case():
    fig, ax = canvas(10, 6.4)
    ax.add_patch(FancyBboxPatch((22, 2), 56, 60, boxstyle="round,pad=0.3,rounding_size=2", fc="white", ec=INK, lw=1.1))
    ax.text(50, 59, "DeepCrop system", ha="center", fontweight="bold")

    def actor(x, y, name):
        ax.add_patch(plt.Circle((x, y + 9), 2, fc="white", ec=INK))
        ax.plot([x, x], [y + 7, y + 2], color=INK)
        ax.plot([x - 3, x + 3], [y + 5.5, y + 5.5], color=INK)
        ax.plot([x, x - 2.5], [y + 2, y - 2], color=INK)
        ax.plot([x, x + 2.5], [y + 2, y - 2], color=INK)
        ax.text(x, y - 5, name, ha="center", fontsize=10)

    actor(9, 36, "Grower /\nexaminer")
    actor(91, 40, "ESP32 field\nunit")
    actor(91, 12, "Ollama LLM")
    cases = [(50, 51, "View live conditions"), (50, 43, "Scan a leaf photo"), (50, 35, "Assess disease risk"),
             (50, 27, "Get grounded advice"), (50, 19, "View sensor history"), (50, 11, "Switch crop module")]
    for x, y, t in cases:
        ax.add_patch(Ellipse((x, y), 30, 6, fc=GREY, ec=INK))
        ax.text(x, y, t, ha="center", va="center", fontsize=10)
    for _, y, _ in cases:
        ax.plot([12, 35], [41, y], color=INK, lw=0.8)
    ax.plot([88, 65], [45, 51], color=INK, lw=0.8)
    ax.text(77, 49.5, "sends readings", fontsize=8.5, color=GREEN, style="italic")
    for y in (35, 27):
        ax.plot([88, 65], [17, y], color=INK, lw=0.8)
    save(fig, "fig_use_case.png")


def er():
    fig, ax = canvas(11, 7)
    ents = {
        "CropModule": (2, 50, "CropModule\nid (PK) · name\nversion · status"),
        "Plant": (40, 50, "Plant\nid (PK) · crop_id (FK)\nname · growth_stage"),
        "Device": (78, 50, "Device\nid (PK) · plant_id (FK)\nstatus · last_seen"),
        "SensorReading": (2, 24, "SensorReading\nid (PK) · plant_id · device_id\nmoisture · ph · temp · humidity\ndata_source · timestamp"),
        "ImagePrediction": (40, 24, "ImagePrediction\nid (PK) · plant_id (FK)\ndisease · confidence\nclass_probabilities · model_version"),
        "DiseaseRiskPrediction": (78, 24, "DiseaseRiskPrediction\nid (PK) · plant_id (FK)\nrisk_score · risk_level\ncomponents · model_status"),
        "Recommendation": (40, 0, "Recommendation\nid (PK) · plant_id (FK)\nsummary · actions · sources\nllm_provider · urgency"),
    }
    for _, (x, y, t) in ents.items():
        box(ax, x, y, 30, 15 if t.count("\n") > 2 else 12, t, fill="white")
    arrow(ax, 32, 56, 40, 56, "1 : N", style="-")
    arrow(ax, 70, 56, 78, 56, "1 : N", style="-")
    arrow(ax, 48, 50, 20, 39, "1 : N", style="-")
    arrow(ax, 55, 50, 55, 39, "1 : N", style="-")
    arrow(ax, 62, 50, 92, 39, "1 : N", style="-")
    arrow(ax, 32, 30, 40, 30, "feeds", style="-")
    arrow(ax, 70, 30, 78, 30, "feeds", style="-")
    arrow(ax, 92, 24, 70, 8, "feeds", style="-")
    save(fig, "fig_er.png")


def dfd():
    fig, ax = canvas(11, 6.4)
    procs = [(14, 40, "1.0\nIngest &\nvalidate"), (40, 40, "2.0\nClassify\nleaf photo"), (66, 40, "3.0\nScore risk\n(3 scorers)"),
             (92, 40, "4.0\nFuse &\nexplain")]
    for x, y, t in procs:
        ax.add_patch(plt.Circle((x, y), 8.5, fc=GREY, ec=INK))
        for i, line in enumerate(t.split("\n")):
            ax.text(x, y + 3.2 - i * 3.2, line, ha="center", va="center", fontsize=9.5, fontweight="bold" if i == 0 else "normal")
    box(ax, 2, 6, 22, 9, "ESP32 field unit", fill=MINT, bold_first=True)
    box(ax, 30, 6, 22, 9, "Grower (photo)", fill=MINT)
    box(ax, 86, 6, 22, 9, "Dashboard", fill=MINT)
    for x, label in [(18, "D1 Sensor readings"), (46, "D2 Image predictions"), (72, "D3 Risk + advice")]:
        ax.plot([x - 9, x + 9], [56, 56], color=INK)
        ax.plot([x - 9, x + 9], [52, 52], color=INK)
        ax.text(x, 54, label, ha="center", va="center", fontsize=9)
    arrow(ax, 13, 15, 14, 31.5, "readings")
    arrow(ax, 41, 15, 40, 31.5, "photo")
    arrow(ax, 22.5, 40, 31.5, 40)
    arrow(ax, 48.5, 40, 57.5, 40, "class probs")
    arrow(ax, 74.5, 40, 83.5, 40, "3 scores")
    arrow(ax, 92, 31.5, 97, 15, "risk, sources")
    arrow(ax, 14, 48.5, 16, 52)
    arrow(ax, 40, 48.5, 44, 52)
    arrow(ax, 70, 52, 67, 48.5)
    arrow(ax, 22, 56.5, 63, 47.5, rad=-0.45)
    ax.text(42, 63, "last 3 readings", ha="center", fontsize=9, color=GREEN, style="italic")
    save(fig, "fig_dfd.png")


def flowchart():
    fig, ax = canvas(8.2, 10.4)
    steps = [
        (30, 97, "Start: assess risk for a plant", "term"),
        (30, 85, "Load latest sensor reading\nand leaf diagnosis", "proc"),
        (30, 72, "Photo model status ready?", "dec"),
        (30, 59, "Sensor reading available?", "dec"),
        (30, 46, "Retrieve knowledge; LLM answer\npasses grounding checks?", "dec"),
        (30, 31, "Fuse available scores\n(weights renormalised)", "proc"),
        (30, 19, "Store score, level, breakdown\n(model_status = provisional)", "proc"),
        (30, 7, "Show on dashboard", "term"),
    ]
    for x, y, t, kind in steps:
        if kind == "dec":
            ax.add_patch(plt.Polygon([[x, y + 5.5], [x + 22, y], [x, y - 5.5], [x - 22, y]], fc=AMBER, ec=INK))
            for i, line in enumerate(t.split("\n")):
                ax.text(x, y + 1.3 * (len(t.split("\n")) - 1) - i * 2.6, line, ha="center", va="center", fontsize=9.5)
        else:
            box(ax, x - 18, y - 4, 36, 8, t, fill=MINT if kind == "term" else GREY, size=9.5, bold_first=False)
    ys = [97, 85, 72, 59, 46, 31, 19, 7]
    for a, b in zip(ys, ys[1:]):
        top = a - (5.5 if a in (72, 59, 46) else 4)
        bot = b + (5.5 if b in (72, 59, 46) else 4)
        arrow(ax, 30, top, 30, bot, "yes" if a in (72, 59, 46) else "")
    side = {72: "photo score = 1 − P(healthy)", 59: "sensor score from 7-day model", 46: "RAG score with citations"}
    for y, t in side.items():
        ax.text(53, y + 1.8, "no: skip scorer", fontsize=8.5, color=GREEN, style="italic")
        ax.text(53, y - 2.5, f"yes: {t}", fontsize=8.5, color=INK)
    save(fig, "fig_flowchart.png")


def hardware():
    fig, ax = canvas(10, 5)
    box(ax, 36, 16, 28, 22, "ESP32-S3 DevKit\n(WROOM-1 N16R8)\nGPIO 4 · GPIO 1 · GPIO 2\n3V3 · GND · USB-C", fill=MINT)
    box(ax, 2, 36, 24, 10, "DHT22 / AM2302\ntemperature + humidity")
    box(ax, 2, 20, 24, 10, "Soil moisture probe\nresistive, LM393 board")
    box(ax, 2, 4, 24, 10, "Crowtail pH sensor\nanalog, uncalibrated")
    box(ax, 74, 30, 24, 10, "Wi-Fi → FastAPI\nPOST /sensors/reading")
    box(ax, 74, 10, 24, 10, "5 V USB adapter\npower")
    arrow(ax, 26, 41, 36, 33)
    arrow(ax, 26, 25, 36, 27)
    arrow(ax, 26, 9, 36, 21)
    arrow(ax, 64, 31, 74, 35)
    arrow(ax, 74, 15, 64, 22)
    for x, y, t in [(27, 44, "DATA → GPIO 4"), (27, 27.8, "AO → GPIO 1"), (27, 5.2, "SIG → GPIO 2")]:
        ax.text(x, y, t, fontsize=9, color=GREEN, style="italic")
    ax.text(66, 35.5, "JSON", fontsize=9, color=GREEN, style="italic")
    ax.text(68, 14.5, "5 V", fontsize=9, color=GREEN, style="italic")
    save(fig, "fig_hardware.png")


if __name__ == "__main__":
    for f in (architecture, use_case, er, dfd, flowchart, hardware):
        f()
    print("wrote", sorted(p.name for p in OUT.glob("fig_*.png")))

"""
Fill the report's contents-page numbers: render the .docx to PDF with LibreOffice, find the page
each heading and caption lands on, and write pages.json for build.js (front matter in roman
numerals from the acknowledgement page, chapters in arabic from Chapter 1).

Run (from docs/report/build):  node build.js && python pagemap.py && node build.js
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
DOCX = HERE.parent / "DeepCrop_Project_Report.docx"
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, r in vals:
        while n >= v:
            out += r
            n -= v
    return out


def main():
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(HERE), str(DOCX)], check=True,
                   stdout=subprocess.DEVNULL)
    pdf = HERE / (DOCX.stem + ".pdf")
    # Each page's text starts with its footer page number (arabic or roman); drop it
    pages = [re.sub(r"^([0-9]+|[ivxlc]+)\s+", "", norm(p.extract_text() or "")) for p in PdfReader(str(pdf)).pages]
    entries = json.loads((HERE / "entries.json").read_text(encoding="utf-8"))

    front_start = next(i for i, t in enumerate(pages) if t.startswith("acknowledgement"))
    main_start = next(i for i, t in enumerate(pages) if t.startswith("1. introduction"))

    result, missing = {}, []
    for group in ("toc", "figures", "tables"):
        cursor = main_start
        for text in entries[group]:
            key = norm(text)[:45]
            hit = next((i for i in range(cursor, len(pages)) if key in pages[i]), None)
            if hit is None:
                missing.append(text)
                continue
            result[text] = str(hit - main_start + 1)
            cursor = hit
    (HERE / "pages.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"PDF pages: {len(pages)} (front matter from page {front_start + 1}, chapters from page {main_start + 1}); "
          f"mapped {len(result)} entries; missing {len(missing)}")
    for m in missing:
        print("  missing:", m)
    print("front matter pages:", ", ".join(roman(i - front_start + 1) for i in range(front_start, main_start)))
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()

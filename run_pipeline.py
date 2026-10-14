#!/usr/bin/env python3
"""Run the exam pipeline end to end.

    python run_pipeline.py                     # fake sample data -> output/sample/
    python run_pipeline.py --data data/real    # real data (not in git) -> output/real/
    python run_pipeline.py --skip-pdfs         # stop after the SVG charts (the PDFs take ~3 minutes)
    python run_pipeline.py --room              # also re-extract room/seats.csv from the drawing first

Steps: [room/extract_seats.py] -> exam/build_students.py -> exam/plan_seats.py
       -> exam/assign_seats.py -> exam/make_charts.py -> exam/make_pdfs.py
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description="Run the McCosh 50 exam seating pipeline")
p.add_argument("--data", default="data/sample"); p.add_argument("--out", default=None)
p.add_argument("--room", action="store_true", help="re-extract room/seats.csv from the drawing PDF first")
p.add_argument("--skip-pdfs", action="store_true")
a = p.parse_args()
io = ["--data", a.data] + (["--out", a.out] if a.out else [])
steps = (["room/extract_seats.py"] if a.room else []) + ["exam/build_students.py", "exam/plan_seats.py",
         "exam/assign_seats.py", "exam/make_charts.py"] + ([] if a.skip_pdfs else ["exam/make_pdfs.py"])
for s in steps:
    print(f"\n=== {s}", flush=True)
    cmd = [sys.executable, str(ROOT / s)] + ([] if s.startswith("room/") else io)
    if subprocess.run(cmd, cwd=ROOT).returncode: sys.exit(f"step failed: {s}")
print("\nDone.")

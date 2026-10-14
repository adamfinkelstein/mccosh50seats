"""Shared paths, config loading and command-line handling for the exam scripts."""
import argparse, json, sys, tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))           # so `import common.charts` works when run as a script

def load_config():
    return tomllib.load(open(ROOT / "exam" / "exam_config.toml", "rb"))

def args(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--data", default="data/sample", help="input directory (default: data/sample)")
    p.add_argument("--out", default=None, help="output directory (default: output/<name of data dir>)")
    a = p.parse_args()
    a.data = (ROOT / a.data) if not Path(a.data).is_absolute() else Path(a.data)
    a.out = Path(a.out) if a.out else ROOT / "output" / a.data.name
    if not a.out.is_absolute(): a.out = ROOT / a.out
    a.out.mkdir(parents=True, exist_ok=True)
    return a

def room_seats():
    import pandas as pd
    return pd.read_csv(ROOT / "room" / "seats.csv")

def room_geometry():
    return json.load(open(ROOT / "room" / "room_geometry.json"))

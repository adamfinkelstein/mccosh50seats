#!/usr/bin/env python3
"""Step 4: draw the SVG charts -> <out>/charts/*.svg and <out>/seats/<seat_id>.svg

    python exam/make_charts.py --data data/sample [--seats MC-5-D,BR-2-A]

charts/overview.svg      every seat, colored by section
charts/lefthanded.svg    left-handed desks in color
charts/assigned.svg      planned seats in color; left-handed desks inverted (assigned in color, unused in gray)
seats/<seat_id>.svg      one chart per planned seat, highlighted with a ring, arrow and label box
"""
import argparse, sys
import pandas as pd
from settings import ROOT, load_config, room_geometry
import settings
from common.charts import render_svg

def main():
    extra = argparse.ArgumentParser(add_help=False); extra.add_argument("--seats", default=None)
    e, rest = extra.parse_known_args(); sys.argv = [sys.argv[0]] + rest
    a = settings.args(__doc__.splitlines()[0]); cfg = load_config()["exam"]; geom = room_geometry()
    plan = pd.read_csv(a.out / "exam_plan.csv"); title = cfg["room_title"]
    (a.out / "charts").mkdir(exist_ok=True); (a.out / "seats").mkdir(exist_ok=True)
    def write(path, svg): path.write_text(svg, encoding="utf-8")
    write(a.out / "charts" / "overview.svg", render_svg(plan, geom, title)[0])
    write(a.out / "charts" / "lefthanded.svg", render_svg(plan, geom, title,
          subtitle=f"Left-handed desks ({int(plan.left_handed.sum())} seats shown in color)", colored=plan.left_handed)[0])
    n, nl = int(plan.exam_plan.sum()), int((plan.exam_plan & plan.left_handed).sum()); nu = int((~plan.exam_plan & plan.left_handed).sum())
    write(a.out / "charts" / "assigned.svg", render_svg(plan, geom, title,
          subtitle=f"Assigned seats: {n} desks in color · left-handed desks inverted ({nl} assigned in color, {nu} unused in gray)",
          colored=plan.exam_plan, inverted=plan.left_handed)[0])
    ids = e.seats.split(",") if e.seats else list(plan[plan.exam_plan].seat_id)
    bad = []
    for sid in ids:
        svg, info = render_svg(plan, geom, title, highlight=sid)
        write(a.out / "seats" / f"{sid}.svg", svg)
        if not info["clean"]: bad.append(sid)
    print(f"wrote 3 charts and {len(ids)} seat charts -> {a.out}")
    if bad: print(f"WARNING: no clean callout placement for {bad} (check those charts by eye)")

if __name__ == "__main__":
    main()

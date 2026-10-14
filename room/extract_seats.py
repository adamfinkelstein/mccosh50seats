#!/usr/bin/env python3
"""Component 1: extract McCosh 50 seat locations from architectural drawing A-102.00.

    python room/extract_seats.py            # writes room/seats.csv and room/room_geometry.json

Pipeline (all deterministic):
  1. Read the vector line work from the PDF. Chairs are drawn in gray (0.67) as ~160 tiny
     segments written consecutively, so walking the drawing order and cutting whenever the
     running bounding box would exceed one chair (27 pt) isolates each chair.
  2. Keep chair-sized chunks (140-210 segments, at least 14 pt on each side). Floor grilles use
     the same gray but are only ~12x8 pt, so the size test removes them.
  3. Main floor: split into 3 blocks with DBSCAN; balcony: DBSCAN splits directly into 9 rows.
  4. Fit each block's arc center (grid search maximizing how tightly chair radii cluster), then
     split rows wherever sorted radii jump by more than 6 pt (rows are ~29 pt apart).
  5. Handedness: rotate every chair into a common facing direction and compare it (Chamfer
     distance) to a reference chair and that reference's mirror image.
  6. Name seats from the students' point of view (facing the stage): sections Left/Center/Right,
     rows numbered from the front, seats lettered A, B, C... from the student's left. In Main
     Center rows split by the AV booth, the right-hand group ends in Z (W X Y Z; row 13: X Y).
  7. Apply in-room corrections from room_config.toml, convert to feet, and compute smoothed
     display coordinates (even spacing along each row's arc) plus a balcony display shift.
"""
import json, math, tomllib
from pathlib import Path
import numpy as np, pandas as pd, pymupdf
from scipy.spatial import cKDTree
from sklearn.cluster import DBSCAN

ROOT = Path(__file__).resolve().parent.parent
CFG = tomllib.load(open(ROOT / "room" / "room_config.toml", "rb"))
PG = CFG["page"]; FT = PG["pt_per_ft"]; WEST = PG["west_wall_x"]; CL = PG["centerline_y"]
BALC_DX = PG["balcony_east_wall_x"] - PG["main_east_wall_x"]
LET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CODE = {"Main Left": "ML", "Main Center": "MC", "Main Right": "MR",
        "Balcony Left": "BL", "Balcony Center": "BC", "Balcony Right": "BR"}

# ---------------------------------------------------------------- 1-2. chairs from vectors
def gray_segments(pdf):
    page = pymupdf.open(pdf)[0]
    g = CFG["source"]["seat_stroke_gray"]; out = []
    for k, d in enumerate(page.get_drawings()):
        c = d.get("color")
        if c and abs(c[0] - g) < 0.02:
            r = d["rect"]; out.append((k, (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, r.width, r.height))
    return np.array(out)

def chunk_chairs(seq, lim=27.0):
    k = seq[:, 0]; x0 = seq[:, 1] - seq[:, 3] / 2; x1 = seq[:, 1] + seq[:, 3] / 2
    y0 = seq[:, 2] - seq[:, 4] / 2; y1 = seq[:, 2] + seq[:, 4] / 2
    chunks, s = [], 0; bx0, bx1, by0, by1 = x0[0], x1[0], y0[0], y1[0]
    for i in range(1, len(seq)):
        nx0, nx1, ny0, ny1 = min(bx0, x0[i]), max(bx1, x1[i]), min(by0, y0[i]), max(by1, y1[i])
        if k[i] - k[i - 1] <= 6 and nx1 - nx0 <= lim and ny1 - ny0 <= lim:
            bx0, bx1, by0, by1 = nx0, nx1, ny0, ny1
        else:
            chunks.append((s, i)); s = i; bx0, bx1, by0, by1 = x0[i], x1[i], y0[i], y1[i]
    chunks.append((s, len(seq)))
    C = []
    for a, b in chunks:
        C.append(dict(n=b - a, a=a, b=b, cx=(x0[a:b].min() + x1[a:b].max()) / 2, cy=(y0[a:b].min() + y1[a:b].max()) / 2,
                      w=x1[a:b].max() - x0[a:b].min(), h=y1[a:b].max() - y0[a:b].min()))
    return C

def in_region(c, name):
    r = CFG["regions"][name]; return r["x0"] < c["cx"] < r["x1"] and r["y0"] < c["cy"] < r["y1"]

# ---------------------------------------------------------------- 3-4. blocks, arcs, rows
def arc_score(Q, c, s=1.2):
    r = np.hypot(Q[:, 0] - c[0], Q[:, 1] - c[1]); D = r[:, None] - r[None, :]
    return np.exp(-D ** 2 / (2 * s * s)).sum()

def fit_center(Q, xs, ys, refine=False):
    best = None
    for cx in xs:
        for cy in ys:
            sc = arc_score(Q, (cx, cy))
            if best is None or sc > best[0]: best = (sc, cx, cy)
    if refine:
        _, cx0, cy0 = best
        for cx in np.arange(cx0 - 12, cx0 + 12, 1):
            for cy in np.arange(cy0 - 12, cy0 + 12, 1):
                sc = arc_score(Q, (cx, cy))
                if sc > best[0]: best = (sc, cx, cy)
    return best[1], best[2]

def rows_by_radius(Q, center, gap=6.0):
    r = np.hypot(Q[:, 0] - center[0], Q[:, 1] - center[1]); o = np.argsort(r)
    rowid = np.zeros(len(Q), int)
    for j, seg in enumerate(np.split(o, np.where(np.diff(r[o]) > gap)[0] + 1)): rowid[seg] = j + 1
    return rowid

# ---------------------------------------------------------------- 5. handedness
def handedness(chairs, seq, centers):
    def canon(c, extra=0.0):
        pts = seq[c["a"]:c["b"], 1:3].copy(); pts -= pts.mean(0)
        ax, ay = centers[c["block"]]; th = math.atan2(ay - c["cy"], ax - c["cx"]) + extra
        R = np.array([[math.cos(-th), -math.sin(-th)], [math.sin(-th), math.cos(-th)]])
        return pts @ R.T
    rots = np.radians(np.arange(-12, 13, 2))
    for var in (True, False):                                   # two chair drawings (~160 vs ~167 segments)
        group = [c for c in chairs if (c["n"] < 164) == var]
        ref = canon(group[len(group) // 2]); T, Tm = cKDTree(ref), cKDTree(ref * [1, -1])
        for c in group:
            ds = min(T.query(canon(c, e))[0].mean() for e in rots)
            dm = min(Tm.query(canon(c, e))[0].mean() for e in rots)
            c["mirror"] = dm < ds
        if sum(c["mirror"] for c in group) > len(group) / 2:     # reference happened to be mirrored
            for c in group: c["mirror"] = not c["mirror"]
    for c in chairs: c["lh"] = c["mirror"]

# ---------------------------------------------------------------- main
def main():
    pdf = ROOT / CFG["source"]["drawing"]
    if not pdf.exists():
        raise SystemExit(f"Drawing not found: {pdf}\nSee README.md (the drawing is not in the public repo).")
    seq = gray_segments(pdf)
    C = chunk_chairs(seq)
    chairs = [c for c in C if (in_region(c, "main") or in_region(c, "balcony"))
              and 140 <= c["n"] <= 210 and min(c["w"], c["h"]) >= 14]
    main_ch = [c for c in chairs if c["cx"] < 1500]; bal_ch = [c for c in chairs if c["cx"] > 1500]
    print(f"chairs found: {len(chairs)} (main {len(main_ch)}, balcony {len(bal_ch)})")

    # main floor blocks (north / middle / south on the sheet)
    P = np.array([[c["cx"], c["cy"]] for c in main_ch])
    lab = DBSCAN(eps=30, min_samples=2).fit(P).labels_
    cents = {l: P[lab == l].mean(0) for l in set(lab) if l >= 0}
    for i in np.where(lab < 0)[0]:                              # isolated chair -> nearest block
        lab[i] = min(cents, key=lambda l: np.hypot(*(P[i] - cents[l])))
    by_y = sorted(cents, key=lambda l: cents[l][1]); name = dict(zip(by_y, ["north", "middle", "south"]))
    for c, l in zip(main_ch, lab): c["block"] = name[l]
    centers = {}
    for blk in ("north", "south"):
        Q = np.array([[c["cx"], c["cy"]] for c in main_ch if c["block"] == blk])
        centers[blk] = fit_center(Q, np.arange(700, 1150, 10), np.arange(300, 1250, 10), refine=True)
    Q = np.array([[c["cx"], c["cy"]] for c in main_ch if c["block"] == "middle"])
    centers["middle"] = fit_center(Q, np.arange(200, 1000, 10), np.arange(600, 950, 5))

    # balcony: DBSCAN gives rows directly; sections by vertical position
    B = np.array([[c["cx"], c["cy"]] for c in bal_ch])
    blab = DBSCAN(eps=24, min_samples=2).fit(B).labels_
    for c, l in zip(bal_ch, blab):
        y = B[blab == l][:, 1].mean(); c["block"] = "bnorth" if y < 650 else "bsouth" if y > 900 else "bmiddle"
    for blk in ("bnorth", "bmiddle", "bsouth"):
        Q = np.array([[c["cx"], c["cy"]] for c in bal_ch if c["block"] == blk])
        centers[blk] = fit_center(Q, np.arange(1000, 1900, 10), np.arange(400, 1150, 10))

    handedness(chairs, seq, centers)

    # rows and stage-view seat order (along each arc), then student-view naming
    student = {"north": "Main Right", "middle": "Main Center", "south": "Main Left",
               "bnorth": "Balcony Right", "bmiddle": "Balcony Center", "bsouth": "Balcony Left"}
    recs = []
    for blk, sec in student.items():
        grp = [c for c in chairs if c["block"] == blk]
        Q = np.array([[c["cx"], c["cy"]] for c in grp]); rid = rows_by_radius(Q, centers[blk])
        for row in sorted(set(rid)):
            members = [grp[i] for i in np.where(rid == row)[0]]
            cx, cy = centers[blk]
            members.sort(key=lambda c: math.atan2(c["cy"] - cy, c["cx"] - cx))
            n = len(members)
            for k, c in enumerate(members, 1):
                bal = blk.startswith("b"); px = c["cx"] - (BALC_DX if bal else 0)
                recs.append(dict(level="Balcony" if bal else "Main", section=sec, row=int(row), seat=n - k + 1,
                                 left_handed=bool(c["lh"]), x_ft=round((CL - c["cy"]) / FT, 2),
                                 y_ft=round((px - WEST) / FT, 2), _blk=blk))
    df = pd.DataFrame(recs)

    # in-room corrections: drop outer seats
    for o in CFG["overrides"].get("drop_outer_seat", []):
        m = (df.section == o["section"]) & (df.row == o["row"])
        side = df[m & ((df.x_ft <= 0) if o["side"] == "left" else (df.x_ft > 0))].sort_values("seat")
        df = df.drop(side.index[0] if o["side"] == "left" else side.index[-1])
        m = (df.section == o["section"]) & (df.row == o["row"])
        df.loc[m, "seat"] = df[m].seat.rank().astype(int)
    last_main = df[df.level == "Main"].y_ft.max(); first_bal = df[df.level == "Balcony"].y_ft.min()
    shift = round(last_main - first_bal + 12.0, 2)                # balcony display shift (ft)

    # letters; Main Center booth-split rows: right-hand group ends in Z (row 13: X Y)
    df["seat_letter"] = [LET[s - 1] for s in df.seat]
    for row in (11, 12, 13):
        m = (df.section == "Main Center") & (df.row == row) & (df.x_ft > 0)
        idx = df[m].sort_values("seat").index; k = len(idx)
        if k: df.loc[idx, "seat_letter"] = list(LET[23:23 + k]) if row == 13 else list(LET[26 - k:])
    df["seat_id"] = [f"{CODE[s]}-{r}-{l}" for s, r, l in zip(df.section, df.row, df.seat_letter)]
    for sid, val in CFG["overrides"].get("left_handed", {}).items():
        assert (df.seat_id == sid).any(), f"override for unknown seat {sid}"
        df.loc[df.seat_id == sid, "left_handed"] = bool(val)

    # display coordinates: even spacing along each row's arc (per unbroken run), balcony shifted back
    df["plot_x"] = df.x_ft.astype(float); df["plot_y"] = df.y_ft.astype(float)
    for (sec, row), g in df.groupby(["section", "row"]):
        blk = g._blk.iloc[0]; px_, py_ = centers[blk]; px_ -= BALC_DX if blk.startswith("b") else 0
        CX = (CL - py_) / FT; CY = (px_ - WEST) / FT
        g = g.sort_values("seat"); xy = g[["x_ft", "y_ft"]].values
        runs = np.split(np.arange(len(g)), np.where(np.hypot(*np.diff(xy, axis=0).T) > 3.3)[0] + 1)
        for run in runs:
            if len(run) < 3: continue
            gg = g.iloc[run]; th = np.unwrap(np.arctan2(gg.y_ft - CY, gg.x_ft - CX))
            r = np.hypot(gg.x_ft - CX, gg.y_ft - CY).mean(); t = np.linspace(th[0], th[-1], len(gg))
            df.loc[gg.index, "plot_x"] = (CX + r * np.cos(t)).round(2); df.loc[gg.index, "plot_y"] = (CY + r * np.sin(t)).round(2)
    df["plot_y"] = (df.plot_y + np.where(df.level == "Balcony", shift, 0)).round(2)

    order = list(CODE)
    df["section_code"] = df.section.map(CODE)
    df["_o"] = df.section.map(order.index)
    df = df.sort_values(["_o", "row", "seat"]).reset_index(drop=True)
    cols = ["seat_id", "section_code", "level", "section", "row", "seat", "seat_letter", "left_handed",
            "x_ft", "y_ft", "plot_x", "plot_y"]
    df[cols].to_csv(ROOT / "room" / "seats.csv", index=False)

    F = CFG["features"]; st, rp, bo = F["stage"], F["ramp"], F["booth"]
    geom = {
        "units": "feet; x = right of centerline as students face the stage, y = back from the stage wall",
        "room": {"x0": -PG["room_half_width_ft"], "x1": PG["room_half_width_ft"], "y0": 0.0, "y1": PG["room_depth_ft"]},
        "stage": {"x0": round((CL - st["y_south"]) / FT, 3), "x1": round((CL - st["y_north"]) / FT, 3),
                  "depth": round((st["x_front"] - WEST) / FT, 3), "corner_radius": st["corner_radius_ft"]},
        "ramp": {"x0": round((CL - rp["y_south"]) / FT, 3), "x1": round((CL - rp["y_north"]) / FT, 3),
                 "y0": round((rp["x_west"] - WEST) / FT, 3), "y1": round((rp["x_east"] - WEST) / FT, 3)},
        "booth": {"x0": round((CL - bo["y_south"]) / FT, 3), "x1": round((CL - bo["y_north"]) / FT, 3),
                  "y0": round((bo["x_west"] - WEST) / FT, 3), "y1": round((bo["x_east"] - WEST) / FT, 3)},
        "balcony_display_shift": shift,
        "unverified_left_handed": CFG["overrides"].get("unverified_left_handed", {}).get("seats", []),
    }
    json.dump(geom, open(ROOT / "room" / "room_geometry.json", "w"), indent=2)
    cnt = df.groupby("section", sort=False).size().to_dict()
    print(f"seats: {len(df)}  left-handed: {int(df.left_handed.sum())}  by section: {cnt}")
    print("wrote room/seats.csv and room/room_geometry.json")

if __name__ == "__main__":
    main()

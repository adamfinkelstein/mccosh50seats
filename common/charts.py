"""Shared SVG rendering of the McCosh 50 seating chart.

render_svg(seats, geom, ...) returns (svg_text, info). `seats` is the room seat table
(room/seats.csv as a DataFrame); `geom` is room/room_geometry.json as a dict.

Seats are hollow circles in their section color with the seat letter inside. Optional:
  colored   - boolean Series; seats not colored are drawn gray
  inverted  - boolean Series; drawn as solid circles with white letters (color if colored, else gray)
  highlight - a seat_id; draws a ring around it and a callout box with an arrow
"""
import math

SIDE = {"Left": "#1F5FA8", "Center": "#1B7F4B", "Right": "#C2570C"}
COL = {f"{lv} {sd}": c for lv in ("Main", "Balcony") for sd, c in SIDE.items()}
GRAY, INK = "#BDBDBD", "#111111"
SC = 12.0                 # px per foot
R = 11.0                  # seat circle radius (px)
BAL_DY = 2.0              # extra ft between balcony section titles and the first balcony row
BAL_PAD = 15.5            # ft of open space below the balcony rows (room for callout boxes)


def render_svg(seats, geom, title="McCosh 50 Seating", subtitle=None,
               colored=None, inverted=None, highlight=None):
    df = seats.copy()
    df["c_colored"] = True if colored is None else colored.values
    df["c_inv"] = False if inverted is None else inverted.values
    bal_top0 = df[df.level == "Balcony"].plot_y.min()
    df.loc[df.level == "Balcony", "plot_y"] += BAL_DY

    ML, MR, MB = 60, 60, 30
    MT = 118 if subtitle else 92
    XMIN, XMAX = -41, 41
    YMAX = df.plot_y.max() + BAL_PAD + 1
    W = int((XMAX - XMIN) * SC + ML + MR); H = int(YMAX * SC + MT + MB)
    P = lambda x, y: (ML + (x - XMIN) * SC, MT + y * SC)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{W/2}" y="52" text-anchor="middle" font-size="30" font-weight="bold" fill="#222">{title}</text>']
    if subtitle:
        o.append(f'<text x="{W/2}" y="84" text-anchor="middle" font-size="17" fill="#333">{subtitle}</text>')

    # room, stage, ramp, AV booth
    rm = geom["room"]; a, b = P(rm["x0"], rm["y0"]); c, d = P(rm["x1"], rm["y1"])
    o.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="none" stroke="#999" stroke-width="1.2"/>')
    st = geom["stage"]; sx0, sx1, sd, rr = st["x0"], st["x1"], st["depth"], st["corner_radius"]
    p0, p1 = P(sx0, 0), P(sx1, 0); q1, q2 = P(sx1, sd - rr), P(sx1 - rr, sd); q3, q4 = P(sx0 + rr, sd), P(sx0, sd - rr)
    R2 = rr * SC
    o.append(f'<path d="M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{q1[0]:.1f},{q1[1]:.1f} '
             f'A{R2},{R2} 0 0 1 {q2[0]:.1f},{q2[1]:.1f} L{q3[0]:.1f},{q3[1]:.1f} A{R2},{R2} 0 0 1 {q4[0]:.1f},{q4[1]:.1f} Z" '
             f'fill="#efebe2" stroke="#888" stroke-width="1.2"/>')
    cx, cy = P((sx0 + sx1) / 2, sd / 2)
    o.append(f'<text x="{cx:.1f}" y="{cy+5:.1f}" text-anchor="middle" font-size="14" fill="#555" letter-spacing="3">STAGE</text>')
    rp = geom["ramp"]; r0, r1 = P(rp["x0"], rp["y0"]), P(rp["x1"], rp["y1"])
    o.append(f'<rect x="{r0[0]:.1f}" y="{r0[1]:.1f}" width="{r1[0]-r0[0]:.1f}" height="{r1[1]-r0[1]:.1f}" fill="#f4f4f4" stroke="#888" stroke-width="1.2"/>')
    cx, cy = P((rp["x0"] + rp["x1"]) / 2, (rp["y0"] + rp["y1"]) / 2)
    o.append(f'<text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" font-size="11" fill="#666">ramp</text>')
    bo = geom["booth"]; (bx0, by0), (bx1, by1) = P(bo["x0"], bo["y0"]), P(bo["x1"], bo["y1"])
    o.append(f'<rect x="{bx0}" y="{by0}" width="{bx1-bx0}" height="{by1-by0}" fill="#f2f2f2" stroke="#999"/>'
             f'<text x="{(bx0+bx1)/2}" y="{(by0+by1)/2+4}" text-anchor="middle" font-size="11" fill="#777">AV booth</text>')
    OBST = [(p0[0], p0[1], p1[0], P(sx1, sd)[1]), (r0[0], r0[1], r1[0], r1[1]), (bx0, by0, bx1, by1)]

    bal = df[df.level == "Balcony"]
    a3, b3 = P(rm["x0"], bal_top0 - 4.8); c3, d3 = P(rm["x1"], bal.plot_y.max() + BAL_PAD)
    REGION = {"Main": (a, b, c, d), "Balcony": (a3, b3, c3, d3)}
    o.append(f'<rect x="{a3}" y="{b3}" width="{c3-a3}" height="{d3-b3}" fill="none" stroke="#999" stroke-width="1.2"/>')

    # seats
    for s in df.itertuples():
        x, y = P(s.plot_x, s.plot_y); col = COL[s.section] if s.c_colored else GRAY
        if highlight and s.seat_id != highlight: col = GRAY
        solid = bool(s.c_inv)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R}" fill="{col if solid else "#fff"}" stroke="{col}" stroke-width="1.4"/>'
                 f'<text x="{x:.1f}" y="{y+4.6:.1f}" text-anchor="middle" font-size="13" font-weight="bold" '
                 f'fill="{"#fff" if solid else col}">{s.seat_letter}</text>')

    # row numbers (just beyond seat A) and section titles; remembered as no-go areas for callouts
    LABELS = []
    for (sec, row), g in df.groupby(["section", "row"]):
        s1 = g[g.seat == 1].iloc[0]; x, y = P(s1.plot_x, s1.plot_y)
        if len(g) > 1:
            s2 = g[g.seat == 2].iloc[0]; x2, y2 = P(s2.plot_x, s2.plot_y); dx, dy = x - x2, y - y2
            n = math.hypot(dx, dy); x += dx / n * 28; y += dy / n * 28
        else:
            x -= 28
        LABELS.append((x - 11, y - 8, x + 11, y + 8))
        o.append(f'<text x="{x:.1f}" y="{y+6:.1f}" text-anchor="middle" font-size="17" font-weight="bold" fill="{COL[sec]}">{row}</text>')
    for sec, g in df.groupby("section"):
        yy = 56.4 if sec.startswith("Main") else bal_top0 - 2.1
        x, y = P(g.plot_x.mean(), yy); label = f"{sec} ({g.section_code.iloc[0]})"
        tw = len(label) * 11.5; LABELS.append((x - tw / 2, y - 10, x + tw / 2, y + 13))
        o.append(f'<text x="{x:.1f}" y="{y+7:.1f}" text-anchor="middle" font-size="21" font-weight="bold" fill="{COL[sec]}">{label}</text>')

    info = {}
    if highlight:
        info = _callout(o, df, P, highlight, LABELS, OBST, REGION)
    o.append("</svg>")
    return "\n".join(o), info


def _callout(o, df, P, seat_id, LABELS, OBST, REGION):
    """Ring + arrow + box for one seat. Placement rules:
    balcony: box in the open strip below the rows, under the seat, slid sideways to clear row numbers;
    main floor: box near the center of the seat's own section, else neighbor sections
    (Left: L,C,R; Center: C,R,L; Right: R,C,L), with nudges; it must stay inside the level,
    avoid stage/ramp/booth, not touch the ring, and the arrow must be >= 45 px and cross no labels."""
    t = df[df.seat_id == seat_id].iloc[0]; col = COL[t.section]; tx, ty = P(t.plot_x, t.plot_y)
    R1 = R + 9
    o.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{R1}" fill="none" stroke="{INK}" stroke-width="3"/>')
    o.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{R}" fill="#fff" stroke="{col}" stroke-width="2.4"/>'
             f'<text x="{tx:.1f}" y="{ty+4.6:.1f}" text-anchor="middle" font-size="13" font-weight="bold" fill="{col}">{t.seat_letter}</text>')
    lvl, side = t.section.split()
    lefty = bool(t.left_handed); BW, BH = 226, (98 if lefty else 76)
    order = {"Left": ["Left", "Center", "Right"], "Center": ["Center", "Right", "Left"], "Right": ["Right", "Center", "Left"]}[side]

    def box_at(sec):
        g = df[df.section == sec]; cx, cy = P(g.plot_x.mean(), g.plot_y.mean()); return cx - BW / 2, cy - BH / 2
    def hits(bx, by, pad=14):
        nx = min(max(tx, bx), bx + BW); ny = min(max(ty, by), by + BH); return math.hypot(tx - nx, ty - ny) < R1 + pad
    def arrow(bx, by):
        bcx, bcy = bx + BW / 2, by + BH / 2; dx, dy = tx - bcx, ty - bcy; d = math.hypot(dx, dy) or 1e-9; ux, uy = dx / d, dy / d
        sc = min((BW / 2) / abs(ux) if ux else 1e9, (BH / 2) / abs(uy) if uy else 1e9)
        sx, sy = bcx + ux * (sc + 4), bcy + uy * (sc + 4); ex, ey = tx - ux * (R1 + 3), ty - uy * (R1 + 3)
        return sx, sy, ex, ey, (math.hypot(ex - sx, ey - sy) if d > sc + R1 + 7 else 0)
    def conflicts(bx, by, sx, sy, ex, ey, pad=4):
        for (x0, y0, x1, y1) in LABELS:
            if bx < x1 + pad and bx + BW > x0 - pad and by < y1 + pad and by + BH > y0 - pad: return True
            n = int(max(abs(ex - sx), abs(ey - sy)) / 2) + 1
            for i in range(n + 1):
                px = sx + (ex - sx) * i / n; py = sy + (ey - sy) * i / n
                if x0 - pad < px < x1 + pad and y0 - pad < py < y1 + pad: return True
        return False
    def inside(bx, by, m=6):
        x0, y0, x1, y1 = REGION[lvl]; return bx >= x0 + m and by >= y0 + m and bx + BW <= x1 - m and by + BH <= y1 - m
    def on_obst(bx, by, pad=4):
        return any(bx < x1 + pad and bx + BW > x0 - pad and by < y1 + pad and by + BH > y0 - pad for (x0, y0, x1, y1) in OBST)

    clean = True
    if lvl == "Balcony":
        x0, y0, x1, y1 = REGION["Balcony"]; _, low = P(0, df[df.level == "Balcony"].plot_y.max())
        by = low + R + 48
        for dx in (0, 25, -25, 50, -50, 75, -75, 100, -100, 130, -130, 160, -160):
            bx = min(max(tx - BW / 2 + dx, x0 + 10), x1 - 10 - BW)
            sx, sy, ex, ey, L = arrow(bx, by)
            if not conflicts(bx, by, sx, sy, ex, ey, pad=6): break
        else:
            clean = False
        where = "below balcony rows"
    else:
        offs = sorted({(dx, dy) for dx in (0, -40, 40, -80, 80) for dy in (0, -40, 40, -80, 80, -120, 120, 160)},
                      key=lambda p: (p[0] ** 2 + p[1] ** 2, abs(p[0])))
        done = False
        for sd in order:
            cx0, cy0 = box_at(f"{lvl} {sd}")
            for dx, dy in offs:
                bx, by = cx0 + dx, cy0 + dy
                if not inside(bx, by) or on_obst(bx, by) or hits(bx, by): continue
                sx, sy, ex, ey, L = arrow(bx, by)
                if L >= 45 and not conflicts(bx, by, sx, sy, ex, ey): done = True; break
            if done: break
        if not done:
            clean = False; bx, by = box_at(f"{lvl} {order[0]}"); sx, sy, ex, ey, L = arrow(bx, by)
        where = f"{lvl} {sd}" if done else "fallback"
    bcx = bx + BW / 2
    o.insert(1, f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>')
    o.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{INK}" stroke-width="4" marker-end="url(#ah)"/>')
    o.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{BW}" height="{BH}" rx="10" fill="#fff" stroke="{INK}" stroke-width="3"/>')
    o.append(f'<text x="{bcx:.1f}" y="{by+35:.1f}" text-anchor="middle" font-size="28" font-weight="bold" fill="{INK}">{seat_id}</text>')
    o.append(f'<text x="{bcx:.1f}" y="{by+61:.1f}" text-anchor="middle" font-size="14.5" fill="{INK}">'
             f'{t.section} · Row {t.row} · Seat {t.seat_letter}</text>')
    if lefty:
        o.append(f'<text x="{bcx:.1f}" y="{by+84:.1f}" text-anchor="middle" font-size="14.5" font-style="italic" fill="{INK}">(Left-handed desk)</text>')
    return {"placement": where, "clean": clean}

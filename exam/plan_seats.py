#!/usr/bin/env python3
"""Step 2: choose which seats are used -> exam_plan.csv

    python exam/plan_seats.py --data data/sample

Reads room/seats.csv, <out>/students.csv and the [plan] section of exam/exam_config.toml.
Writes <out>/exam_plan.csv: the room seat table plus a boolean `exam_plan` column.

Rules (see exam_config.toml): strict every-other-seat patterns in every row; exactly as many
left-handed desks as left-handed students; reserved rows unused; "avoid" rows unused if the
room still fits everyone; fixed patterns honored. Among valid plans, minimize aisle-end repeats
between consecutive rows, then minimize seats given up. Solved exactly by dynamic programming
over the rows of each section, then combining sections.
"""
import itertools, sys
import pandas as pd
from settings import args, load_config, room_seats

def solve(df, P, n_lefty, need, avoid):
    booth = set(P["booth_split_rows"])
    fixed = {(f["section"], f["row"], f["group"]): f["side"] for f in P.get("fixed_patterns", [])}
    reserved = [(r["level"], r["row"]) for r in P.get("reserved_rows", [])]
    avoid_set = {(r["section"], r["row"]) for r in P.get("avoid_rows_if_possible", [])} if avoid else set()
    def excluded(sec, row):
        return any(sec.startswith(lv) and row == r for lv, r in reserved) or (sec, row) in avoid_set
    def groups_of(sec, row, R):
        R = R.sort_values("seat")
        if sec == "Main Center" and row in booth:
            return [("left", R[R.x_ft <= 0], ("Lend", "boothL")), ("right", R[R.x_ft > 0], ("boothR", "Rend"))]
        return [("full", R, ("Lend", "Rend"))]
    def group_options(sec, row, gname, g, ends):
        n = len(g); lh = g.left_handed.values; out = []
        pats = {"L": list(range(0, n, 2)), "R": list(range(1, n, 2))} if n % 2 == 0 else {"O": list(range(0, n, 2))}
        if (sec, row, gname) in fixed:
            side = fixed[(sec, row, gname)]
            if side not in pats: sys.exit(f"ERROR: fixed pattern {side} not valid for {sec} row {row} {gname} ({n} seats)")
            pats = {side: pats[side]}
        for name, ix in pats.items():
            occ = set()
            if 0 in ix: occ.add(ends[0])
            if n - 1 in ix: occ.add(ends[1])
            out.append(dict(name=name, idx=[g.index[i] for i in ix], k=int(sum(lh[i] for i in ix)), loss=0, ends=occ))
            if n % 2 == 1:   # odd row may leave its first aisle seat empty (costs one seat)
                ix2 = ix[1:]
                out.append(dict(name="O-", idx=[g.index[i] for i in ix2], k=int(sum(lh[i] for i in ix2)), loss=1, ends={ends[1]}))
        return out

    capacity = 0; tables = {}
    for sec in df.section.unique():
        S = df[df.section == sec]; rows = [r for r in sorted(S.row.unique()) if not excluded(sec, r)]
        if not rows: continue
        row_opts = []
        for r in rows:
            combos = []
            for choice in itertools.product(*[group_options(sec, r, gn, g, e) for gn, g, e in groups_of(sec, r, S[S.row == r])]):
                combos.append(dict(idx=sum((c["idx"] for c in choice), []), k=sum(c["k"] for c in choice),
                                   loss=sum(c["loss"] for c in choice), ends=set().union(*[c["ends"] for c in choice]),
                                   label="/".join(c["name"] for c in choice)))
            row_opts.append(combos)
            capacity += max(len(c["idx"]) + c["loss"] for c in combos)
        tables[sec] = (rows, row_opts)
    budget = min(P.get("max_seats_given_up", 1), capacity - need)
    if budget < 0: return None
    best_by_sec = {}
    for sec, (rows, row_opts) in tables.items():
        layer = {(oi, o["k"], o["loss"]): (0, [oi]) for oi, o in enumerate(row_opts[0])}
        for ri in range(1, len(rows)):
            nl = {}
            for (pi, k, l), (c, path) in layer.items():
                for oi, o in enumerate(row_opts[ri]):
                    kk, ll = k + o["k"], l + o["loss"]
                    if kk > n_lefty or ll > budget: continue
                    rep = len(row_opts[ri - 1][pi]["ends"] & o["ends"]) if rows[ri] == rows[ri - 1] + 1 else 0
                    key = (oi, kk, ll); v = c + rep
                    if key not in nl or v < nl[key][0]: nl[key] = (v, path + [oi])
            layer = nl
        best = {}
        for (oi, k, l), (c, path) in layer.items():
            if (k, l) not in best or c < best[(k, l)][0]:
                best[(k, l)] = (c, [s for ri, p in enumerate(path) for s in row_opts[ri][p]["idx"]],
                                {rows[ri]: row_opts[ri][p]["label"] for ri, p in enumerate(path)})
        best_by_sec[sec] = best
    comb = {(0, 0): (0, [], {})}
    for sec, t in best_by_sec.items():
        nc = {}
        for (k0, l0), (c0, s0, lab0) in comb.items():
            for (k, l), (c, s, lab) in t.items():
                kk, ll = k0 + k, l0 + l
                if kk > n_lefty or ll > budget: continue
                v = c0 + c
                if (kk, ll) not in nc or v < nc[(kk, ll)][0]: nc[(kk, ll)] = (v, s0 + s, {**lab0, sec: lab})
        comb = nc
    cands = [(v[0], l, v[1], v[2]) for (k, l), v in comb.items() if k == n_lefty and len(v[1]) >= need]
    if not cands: return None
    rep, loss, seats, labels = min(cands, key=lambda t: (t[0], t[1]))
    return dict(seats=seats, repeats=rep, given_up=loss, labels=labels, capacity=capacity)

def main():
    a = args(__doc__.splitlines()[0]); P = load_config()["plan"]
    df = room_seats(); st = pd.read_csv(a.out / "students.csv", dtype=str, keep_default_na=False)
    n_lefty = int((st.Special == "Left").sum()); need = int((st.Special != "Accom").sum())
    if n_lefty > int(df.left_handed.sum()): sys.exit(f"ERROR: {n_lefty} left-handed students but only {int(df.left_handed.sum())} left-handed desks")
    res = solve(df, P, n_lefty, need, avoid=True); used_avoid_rows = False
    if res is None:
        res = solve(df, P, n_lefty, need, avoid=False); used_avoid_rows = True
    if res is None:
        sys.exit(f"ERROR: no valid plan seats {need} students with exactly {n_lefty} at left-handed desks. "
                 "Relax [plan] settings in exam/exam_config.toml.")
    df["exam_plan"] = False; df.loc[res["seats"], "exam_plan"] = True
    df.to_csv(a.out / "exam_plan.csv", index=False)
    sel = df[df.exam_plan]
    print(f"seats used: {len(sel)} (need {need})  left-handed desks used: {int(sel.left_handed.sum())}  "
          f"aisle-end repeats: {res['repeats']}  seats given up: {res['given_up']}  "
          f"'avoid' rows {'USED' if used_avoid_rows else 'left empty'}  -> {a.out / 'exam_plan.csv'}")
    for sec, lab in res["labels"].items():
        print(f"  {sec:15s}", " ".join(f"{r}:{l}" for r, l in lab.items()))

if __name__ == "__main__":
    main()

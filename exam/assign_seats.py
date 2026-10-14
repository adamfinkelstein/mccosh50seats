#!/usr/bin/env python3
"""Step 3: randomly assign students to the planned seats -> students_seated.csv

    python exam/assign_seats.py --data data/sample

Left-handed students are shuffled onto the left-handed desks in the plan, everyone else onto
the remaining plan seats; students in the extra room get Seat = "". Uses random.Random(seed)
with seed from exam_config.toml (default 0), so re-running gives the same assignment.
"""
import random, sys
import pandas as pd
from settings import args, load_config

def main():
    a = args(__doc__.splitlines()[0]); seed = load_config()["exam"]["seed"]
    st = pd.read_csv(a.out / "students.csv", dtype=str, keep_default_na=False)
    plan = pd.read_csv(a.out / "exam_plan.csv"); plan = plan[plan.exam_plan]
    lefty_seats = list(plan[plan.left_handed].seat_id); other_seats = list(plan[~plan.left_handed].seat_id)
    L = st.index[st.Special == "Left"].tolist(); N = st.index[st.Special == ""].tolist()
    if len(L) != len(lefty_seats) or len(N) > len(other_seats):
        sys.exit(f"ERROR: plan has {len(lefty_seats)} left-handed / {len(other_seats)} other seats for "
                 f"{len(L)} left-handed / {len(N)} other students. Re-run plan_seats.py.")
    rng = random.Random(seed)
    rng.shuffle(lefty_seats); rng.shuffle(other_seats)
    st["Seat"] = ""
    st.loc[L, "Seat"] = lefty_seats; st.loc[N, "Seat"] = other_seats[:len(N)]
    lh = set(plan[plan.left_handed].seat_id); seated = st[st.Seat != ""]
    assert seated.Seat.is_unique and st.loc[L, "Seat"].isin(lh).all() and not st.loc[N, "Seat"].isin(lh).any()
    st.to_csv(a.out / "students_seated.csv", index=False)
    spare = len(other_seats) - len(N)
    print(f"seated {len(seated)} students (seed {seed}); {len(st) - len(seated)} in extra room; "
          f"{spare} spare plan seat(s)  -> {a.out / 'students_seated.csv'}")

if __name__ == "__main__":
    main()

"""Component 2: run the pipeline on the fake sample data and check the seating rules."""
import shutil, subprocess, sys
from pathlib import Path
import pandas as pd, pytest

ROOT = Path(__file__).resolve().parent.parent

def run(script, data, out, *extra):
    r = subprocess.run([sys.executable, str(ROOT / script), "--data", str(data), "--out", str(out), *extra],
                       capture_output=True, text=True)
    return r

@pytest.fixture(scope="module")
def out(tmp_path_factory):
    o = tmp_path_factory.mktemp("sample")
    for s in ("exam/build_students.py", "exam/plan_seats.py", "exam/assign_seats.py"):
        r = run(s, ROOT / "data" / "sample", o); assert r.returncode == 0, r.stderr + r.stdout
    return o

def test_students(out):
    st = pd.read_csv(out / "students.csv", dtype=str, keep_default_na=False)
    assert len(st) == 225 and (st.Special == "Left").sum() == 14 and (st.Special == "Accom").sum() == 3

def test_plan_rules(out):
    p = pd.read_csv(out / "exam_plan.csv"); used = p[p.exam_plan]
    assert len(used) == 222 and int(used.left_handed.sum()) == 14
    assert not ((used.level == "Main") & (used.row == 1)).any()                       # row 1 reserved
    assert not ((used.section == "Main Center") & (used.row == 13)).any()             # avoided (enough room)
    assert not used.seat_id.isin(["MC-11-W", "MC-12-W"]).any()                        # fixed patterns
    for (sec, row), R in p.groupby(["section", "row"]):                                # every other seat
        R = R.sort_values("seat"); e = R.exam_plan.tolist(); x = R.x_ft.tolist()
        split = sec == "Main Center" and row in (11, 12, 13)
        for i in range(len(e) - 1):
            assert not (e[i] and e[i + 1] and not (split and x[i] <= 0 < x[i + 1])), (sec, row)

def test_assignment(out):
    st = pd.read_csv(out / "students_seated.csv", dtype=str, keep_default_na=False)
    p = pd.read_csv(out / "exam_plan.csv"); lh = set(p[p.left_handed].seat_id)
    seated = st[st.Seat != ""]
    assert len(seated) == 222 and seated.Seat.is_unique
    assert st[st.Special == "Left"].Seat.isin(lh).all()
    assert not st[st.Special == ""].Seat.isin(lh).any()
    assert (st[st.Special == "Accom"].Seat == "").all()

def test_assignment_reproducible(out, tmp_path):
    shutil.copy(out / "students.csv", tmp_path); shutil.copy(out / "exam_plan.csv", tmp_path)
    assert run("exam/assign_seats.py", ROOT / "data" / "sample", tmp_path).returncode == 0
    assert (tmp_path / "students_seated.csv").read_text() == (out / "students_seated.csv").read_text()

def test_charts_place_callouts_cleanly(out):
    r = run("exam/make_charts.py", ROOT / "data" / "sample", out, "--seats", "ML-8-E,MC-5-D,MR-9-A,BC-2-H,BR-2-A")
    assert r.returncode == 0 and "WARNING" not in r.stdout
    assert (out / "charts" / "assigned.svg").exists() and (out / "seats" / "BR-2-A.svg").exists()

def test_bad_netid_is_rejected(tmp_path):
    d = tmp_path / "data"; shutil.copytree(ROOT / "data" / "sample", d)
    (d / "lefty.txt").write_text("zz9999\n")
    r = run("exam/build_students.py", d, tmp_path / "o")
    assert r.returncode != 0 and "not in the roster" in (r.stderr + r.stdout)

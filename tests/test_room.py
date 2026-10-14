"""Component 1: invariants of room/seats.csv (and, if the drawing is present, that extraction reproduces it)."""
import json, subprocess, sys
from pathlib import Path
import pandas as pd, pytest

ROOT = Path(__file__).resolve().parent.parent
ROWS = {"Main Left":      [2, 6, 8, 10, 12, 14, 13, 11, 10, 9, 9, 8, 8],
        "Main Center":    [3, 8, 9, 10, 10, 11, 12, 12, 13, 14, 8, 8, 4],
        "Main Right":     [2, 6, 8, 10, 12, 13, 11, 10, 9, 9, 8, 8],
        "Balcony Left":   [8, 9, 8], "Balcony Center": [14, 14, 15], "Balcony Right": [8, 9, 9]}

@pytest.fixture(scope="module")
def seats():
    return pd.read_csv(ROOT / "room" / "seats.csv")

def test_total_and_unique(seats):
    assert len(seats) == 442 and seats.seat_id.is_unique

def test_row_counts_match_room(seats):
    for sec, counts in ROWS.items():
        got = seats[seats.section == sec].groupby("row").size().tolist()
        assert got == counts, sec

def test_left_handed_desks(seats):
    assert int(seats.left_handed.sum()) == 32
    assert bool(seats.set_index("seat_id").loc["ML-12-D", "left_handed"])       # verified in room

def test_mc13_has_two_seats_each_side(seats):
    r13 = seats[(seats.section == "Main Center") & (seats.row == 13)]
    assert sorted(r13.seat_letter) == ["A", "B", "X", "Y"]

def test_booth_rows_end_in_z(seats):
    for row in (11, 12):
        r = seats[(seats.section == "Main Center") & (seats.row == row)].sort_values("seat")
        assert "".join(r.seat_letter) == "ABCDWXYZ"

def test_geometry_file():
    g = json.load(open(ROOT / "room" / "room_geometry.json"))
    assert {"room", "stage", "ramp", "booth", "balcony_display_shift"} <= set(g)

@pytest.mark.skipif(not any((ROOT / "room" / "drawing").glob("*.pdf")),
                    reason="architectural drawing not present (it is not in the public repo)")
def test_extraction_reproduces_csv():
    before = (ROOT / "room" / "seats.csv").read_text()
    subprocess.run([sys.executable, str(ROOT / "room" / "extract_seats.py")], check=True, capture_output=True)
    assert (ROOT / "room" / "seats.csv").read_text() == before

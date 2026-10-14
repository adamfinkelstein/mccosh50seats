# McCosh 50 exam seating

Assigns students to seats in **McCosh 50** (McCosh Hall, Princeton University) for exams, with every
other seat left empty, left-handed students placed at left-handed desks, and printable handouts and
per-seat charts. It was built for the COS126 Fall 2026 midterm and is meant to be re-run for later exams.

The repository has two components:

1. **Room** (`room/`, specific to McCosh 50): turns the architectural drawing into a table of all
   442 fixed seats (`room/seats.csv`) with names, positions, and left-handed desks, plus the room
   outline (`room/room_geometry.json`). This rarely needs re-running; its output is committed.
2. **Exam** (`exam/`): takes a roster plus lists of special cases, chooses which seats to use,
   randomly assigns students to them, and produces charts and PDFs.

Real student data never goes in git. The repository ships **fake sample data** (`data/sample/`) with
the same structure as a real class (225 students, 14 left-handed, 3 in an accommodations room), so
everything can be run and tested publicly.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # cairosvg also needs the Cairo system library (see requirements.txt)
python -m pytest -q                      # ~10 s
python run_pipeline.py                   # sample data -> output/sample/   (~3.5 min; --skip-pdfs: ~15 s)
```

For a real exam, put the real inputs in `data/real/` (see `data/real/README.md`) and run
`python run_pipeline.py --data data/real`.

## Seat names

Left and right are **as seen by students facing the stage**; charts are drawn with the stage at the top,
so left/right on the page match the students' view.

* Sections: `ML`, `MC`, `MR` (main floor Left/Center/Right) and `BL`, `BC`, `BR` (balcony).
* Rows are numbered from the front (1 = nearest the stage). Seats are lettered A, B, C… from the
  student's left along the row.
* Main Center rows 11–13 are split by the AV booth: the left part is A, B, C…; the right part ends in Z
  (`W X Y Z`; row 13: `X Y`).
* Seat IDs look like `MC-7-E` (Main Center, row 7, seat E).

## Component 1: room (`room/`)

| file | |
|---|---|
| `extract_seats.py` | drawing PDF → `seats.csv` + `room_geometry.json` (method described in the file's docstring) |
| `room_config.toml` | page coordinates, room features, and **in-room corrections** (seats removed, handedness overrides, unverified desks) |
| `seats.csv` | committed output: `seat_id, section_code, level, section, row, seat, seat_letter, left_handed, x_ft, y_ft, plot_x, plot_y` |
| `room_geometry.json` | committed output: room, stage, ramp and AV booth outlines (feet) and the balcony display shift |
| `drawing/` | where the drawing goes (not committed; see `drawing/README.md`) |

Coordinates: `x_ft` is feet right of the room centerline (students' view), `y_ft` is feet back from the
stage wall; both are true positions from the drawing. `plot_x`/`plot_y` are for drawing only: seats are
spaced evenly along each row's arc, and the balcony (which really sits above the back of the main floor)
is shifted back so the two levels don't overlap.

Seats were checked against the room in October 2026: MC row 13 has 2 seats on each side of the booth
(the drawing shows 3), and ML-12-D is a left-handed desk (beside a pillar). MC-11-W and MC-12-W are drawn
as left-handed desks but have **not** been verified; the exam plan keeps them empty.

**Never edit `seats.csv` by hand.** Record any room change in `room_config.toml` and re-run
`python room/extract_seats.py` (needs the drawing).

## Component 2: exam (`exam/`)

Inputs (in a data directory such as `data/sample/` or `data/real/`):

| file | format |
|---|---|
| `enroll.txt` | `YY/Last/First/Precept/netid/ID/` per line |
| `accommodations.txt` | netids of students taking the exam elsewhere (`extra_room` in the config), one per line, `#` comments |
| `lefty.txt` | netids of students who need a left-handed desk |

Steps (each script takes `--data DIR` and optional `--out DIR`, default `output/<data dir name>/`):

| step | script | output |
|---|---|---|
| 1 | `build_students.py` | `students.csv` (`netid,last,first,precept,year,Special`; Special = `Left`/`Accom`/blank). Fails on unknown or duplicate netids. |
| 2 | `plan_seats.py` | `exam_plan.csv` = `seats.csv` + boolean `exam_plan` |
| 3 | `assign_seats.py` | `students_seated.csv` = students + `Seat` (seeded shuffle; blank for the extra room) |
| 4 | `make_charts.py` | `charts/overview.svg`, `charts/lefthanded.svg`, `charts/assigned.svg`, `seats/<seat_id>.svg` |
| 5 | `make_pdfs.py` | `pdf/handout.pdf`, `pdf/seat_charts.pdf`, `pdf/seat_pdfs.zip` |

`run_pipeline.py` runs them in order.

### Seating rules (`exam/exam_config.toml`)

* **Every other seat** in every row. Odd-length rows use both aisle ends (A, C, E…); even-length rows
  use one end (A, C, E… or B, D, F…). The two sides of the AV booth are not neighbors.
* **Main-floor row 1 is reserved** for late arrivals. **MC row 13** is left empty when everyone fits without it.
* **Exactly as many left-handed desks as left-handed students** are used, and no one else sits at one.
* **MC rows 11–12, right of the booth**, always use X and Z (W's handedness is unverified).
* Among valid plans, the planner minimizes **aisle-end repeats** (the same end seat occupied in two
  consecutive rows), so consecutive even rows alternate sides where possible. Odd rows may leave their
  first aisle seat empty (still every other seat) to improve this; at most `max_seats_given_up` seats.
* The search is exact (dynamic programming over rows, then over sections), not a heuristic.

For the Fall 2026 midterm (222 students in the room, 14 left-handed) this uses 222 of the 223 available
plan seats, with 30 aisle-end repeats.

### Outputs

* `handout.pdf`: course header; overall chart; assigned-seats chart (left-handed desks inverted:
  assigned in color, unused in gray); all students by name; all students by seat.
* `seat_charts.pdf`: overall chart, left-handed map, and one page per seat (bookmarked by section).
* `seat_pdfs.zip`: one Letter-size PDF per seat, `<seat_id>.pdf`, e.g. for emailing each student their seat.

All pages are US Letter portrait with 1/2" margins.

## A new exam: checklist

1. Edit `exam/exam_config.toml`: `course`, `extra_room`, and any policy changes.
2. Put `enroll.txt`, `accommodations.txt` and `lefty.txt` in `data/real/`.
3. If anything changed in the room (or MC-11-W / MC-12-W have been checked), update `room/room_config.toml`
   and re-run `python room/extract_seats.py` (needs the drawing).
4. `python -m pytest -q`, then `python run_pipeline.py --data data/real`.
5. Look at `output/real/pdf/handout.pdf` and spot-check a few seat charts.

## Reproducibility and privacy

* The seat assignment uses `random.Random(seed)` with `seed = 0` from the config, so re-running gives the
  same assignment on the same Python installation. Change the seed to draw a different assignment.
  *Note:* the assignment actually used for the Fall 2026 midterm was drawn before seeding was added, so
  re-running with seed 0 gives a different (equally valid) assignment.
* `data/real/`, `output/` and the drawing PDF are git-ignored. Before every commit, check
  `git status --ignored` and make sure nothing real is staged.
* `tools/make_fake_data.py` regenerates `data/sample/` from real inputs: Faker names, netids = initials +
  4 random digits, random 9-digit IDs; class years, precepts and the special-case pattern are preserved.

## Source drawing

Sheet **A-102.00**, *Summer 2020 – Second Floor and Balcony Construction Plan*, McCosh 50 Summer 2020
Record Drawings (1100 Architect, P.C., record set 2020-10-14), from Princeton University Facilities.
It is not included in this repository; see `room/drawing/README.md`.

## License

MIT; see `LICENSE`.

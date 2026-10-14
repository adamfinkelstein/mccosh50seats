# CLAUDE.md

Guidance for Claude Code working in this repository. Read `README.md` for what the project does.

## Current status

This code was consolidated from an exploratory session into a clean pipeline and verified there:
`room/extract_seats.py` reproduces the finalized `room/seats.csv` exactly, and the exam pipeline
reproduces the finalized Fall 2026 midterm plan exactly. On 2026-10-14 it was reproduced on the
owner's Mac (Python 3.13.16 via pyenv, pinned in `.python-version`): every number below matched, and
re-extraction left `room/seats.csv` byte-identical. It is on GitHub as `adamfinkelstein/mccosh50seats`
(public since 2026-10-14), under the MIT license.

## Reproducing on a new machine

1. **Python 3.11+** is required (`tomllib`). Check with `python3 --version`.
2. **Cairo**, the system library behind `cairosvg`. On macOS: `brew install cairo`; on Debian/Ubuntu:
   `sudo apt install libcairo2`. Symptom if missing: `OSError: no library called "cairo" was found`
   when importing cairosvg. (On Apple Silicon with Homebrew, cairosvg may additionally need
   `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.)
3. Create a virtual environment and install pinned dependencies:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the tests: `python -m pytest -q`. Expect **13 passed** if the drawing PDF is in
   `room/drawing/`, otherwise 12 passed and 1 skipped (`test_extraction_reproduces_csv`).
5. Run the pipeline on the fake sample data:
   ```bash
   python run_pipeline.py --skip-pdfs     # ~15 s
   python run_pipeline.py                 # full run incl. PDFs, ~1-4 min
   ```
   Expected console summary for the sample data:
   - `students: 225  accommodations: 3  left-handed: 14  to seat in the room: 222`
   - `seats used: 222 (need 222)  left-handed desks used: 14  aisle-end repeats: 30  seats given up: 1  'avoid' rows left empty`
   - `wrote 3 charts and 222 seat charts` with **no** `WARNING` line
   - `handout.pdf (12 pages), seat_charts.pdf (224 pages), seat_pdfs.zip (222 files)`
6. If `data/real/` contains `enroll.txt`, `accommodations.txt` and `lefty.txt`, also run
   `python run_pipeline.py --data data/real`. The summary numbers should match step 5 (same
   class structure), with real names in `output/real/`.
7. If the drawing is present, `python run_pipeline.py --room --skip-pdfs` re-extracts the seats first;
   `git diff room/seats.csv` (once in git) or the test above should show no change.
8. Report back to the owner what you ran and whether every expected number matched. If something
   differs, stop and describe it rather than "fixing" outputs.

Open a couple of outputs to sanity-check visually: `output/sample/pdf/handout.pdf` (12 pages:
two charts, then tables by name and by seat) and one or two `output/sample/seats/*.svg`.

## Then: prepare the GitHub repository (only when the owner asks)

1. `git init`; confirm `.gitignore` is in place **before** the first `git add`.
2. `git add -A`, then `git status --ignored` and check that **none** of these are staged:
   `data/real/*` (except its README), `output/`, `room/drawing/*.pdf`, `.venv/`.
   Also grep the staged files for a few real netids or names if real data is on the machine.
3. Things that **should** be committed: all code, `room/seats.csv`, `room/room_geometry.json`, both
   config files, `data/sample/*`, tests, docs.
4. The LICENSE is MIT. The repository is public: re-check the privacy items above before every push.

## Rules and conventions

- **Privacy:** never commit, print into docs, or paste into issues anything from `data/real/` or
  `output/real/`. Use `data/sample/` for examples and tests.
- **Don't hand-edit `room/seats.csv` or `room/room_geometry.json`.** Room changes go in
  `room/room_config.toml` (`[overrides]`), then re-run `room/extract_seats.py`. The extraction needs the
  drawing, which is not in the repo; if it's absent, leave the committed CSV alone.
- If a dependency upgrade makes `test_extraction_reproduces_csv` fail, the extraction changed behavior:
  restore `room/seats.csv` from git and investigate; don't commit a changed seat table without the
  owner's review.
- Exam policy lives in `exam/exam_config.toml`; prefer config changes over code changes.
- Seat assignment is seeded (`seed = 0`): same inputs give the same assignment on the same machine.
  The assignment actually used for the Fall 2026 midterm predates seeding and will not be reproduced.
- Left/right always mean the **students' view facing the stage**; charts put the stage at the top.
- pandas is 3.x: string columns have dtype `str` (not `object`), and `itertuples()` renames columns
  that start with `_`; keep that in mind when editing.

## Layout

```
room/        component 1 (McCosh 50 specific): extract_seats.py, room_config.toml, seats.csv, room_geometry.json
exam/        component 2: build_students, plan_seats, assign_seats, make_charts, make_pdfs, exam_config.toml
common/      charts.py: shared SVG rendering (seat chart, highlight callouts)
tools/       make_fake_data.py
data/sample/ fake inputs (committed)    data/real/ real inputs (ignored)
output/      generated (ignored)        tests/     pytest suite
run_pipeline.py  runs everything in order
```

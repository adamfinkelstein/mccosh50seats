# Real student data (never committed)

Everything in this directory except this README is ignored by git. Put the real inputs here:

| file | format |
|---|---|
| `enroll.txt` | one student per line: `YY/Last/First/Precept/netid/ID/` (e.g. `   30/Chang/Megan/P01/mc6311/913847339/`) |
| `accommodations.txt` | netids of students taking the exam in the extra room, one per line; `#` starts a comment |
| `lefty.txt` | netids of students who need a left-handed desk, one per line; `#` starts a comment |

Then run `python run_pipeline.py --data data/real` (outputs go to `output/real/`, also ignored).
To refresh the fake sample data from these files: `python tools/make_fake_data.py --real data/real --out data/sample`.

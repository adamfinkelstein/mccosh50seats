#!/usr/bin/env python3
"""Step 1: roster + special-case netid lists -> students.csv

    python exam/build_students.py --data data/sample

Inputs (in the data directory; names set in exam/exam_config.toml):
  enroll.txt          one student per line:  YY/Last/First/Precept/netid/ID/
  accommodations.txt  netids of students taking the exam in the extra room
  lefty.txt           netids of students who need a left-handed desk
Output: <out>/students.csv with columns netid,last,first,precept,year,Special
  (Special is "", "Left" or "Accom"). Stops with an error on any inconsistency.
"""
import csv, collections, sys
from settings import args, load_config

def read_netids(path):
    ids = []
    for line in open(path, encoding="utf-8"):
        s = line.split("#")[0].strip()
        if s: ids.append(s.lower())
    return ids

def main():
    a = args(__doc__.splitlines()[0]); cfg = load_config()["inputs"]
    students, errors = [], []
    for i, line in enumerate(open(a.data / cfg["enroll"], encoding="utf-8"), 1):
        s = line.strip()
        if not s: continue
        f = s.rstrip("/").split("/")
        if len(f) != 6: errors.append(f"enroll line {i}: expected 6 fields, got {len(f)}: {s}"); continue
        yy, last, first, precept, netid, _id = (x.strip() for x in f)
        students.append(dict(netid=netid.lower(), last=last, first=first, precept=precept,
                             year=2000 + int(yy), Special=""))
    by_id = {s["netid"]: s for s in students}
    dups = [n for n, c in collections.Counter(s["netid"] for s in students).items() if c > 1]
    if dups: errors.append(f"duplicate netids in roster: {dups}")
    acc, left = read_netids(a.data / cfg["accommodations"]), read_netids(a.data / cfg["lefty"])
    for label, ids in (("accommodations", acc), ("lefty", left)):
        unknown = [n for n in ids if n not in by_id]
        if unknown: errors.append(f"{label} list has netids not in the roster: {unknown}")
        d = [n for n, c in collections.Counter(ids).items() if c > 1]
        if d: errors.append(f"{label} list repeats netids: {d}")
    both = sorted(set(acc) & set(left))
    if both: errors.append(f"netids in both accommodations and lefty lists: {both} (an Accom student needs no desk here)")
    if errors:
        sys.exit("ERROR building students.csv:\n  " + "\n  ".join(errors))
    for n in acc: by_id[n]["Special"] = "Accom"
    for n in left: by_id[n]["Special"] = "Left"
    with open(a.out / "students.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["netid", "last", "first", "precept", "year", "Special"])
        w.writeheader(); w.writerows(students)
    print(f"students: {len(students)}  accommodations: {len(acc)}  left-handed: {len(left)}  "
          f"to seat in the room: {len(students) - len(acc)}  -> {a.out / 'students.csv'}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Make a privacy-safe copy of the real inputs with fake student identities.

    python tools/make_fake_data.py --real data/real --out data/sample [--seed 0]

Keeps everything that matters for seating (number of students, line order, class year, precept,
and which students are on the accommodations / lefty lists) but replaces names with Faker names,
netids with initials + 4 random digits (e.g. "Adam Davis" -> ad6512), and the 9-digit university
IDs with random 9-digit numbers (no leading zero). Seeded, so the sample data is stable.
"""
import argparse, random, re
from pathlib import Path
from faker import Faker

def read_ids(path):
    out = []
    for line in open(path, encoding="utf-8"):
        s = line.split("#")[0].strip()
        if s: out.append(s.lower())
    return out

def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--real", default="data/real"); p.add_argument("--out", default="data/sample")
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args(); real, out = Path(a.real), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fake = Faker("en_US"); Faker.seed(a.seed); rng = random.Random(a.seed)
    clean = lambda s: re.sub(r"[^A-Za-z' -]", "", s)
    mapping, used, lines = {}, set(), []
    for line in open(real / "enroll.txt", encoding="utf-8"):
        s = line.strip()
        if not s: continue
        yy, _last, _first, precept, netid, _id = s.rstrip("/").split("/")
        first, last = clean(fake.first_name()), clean(fake.last_name())
        while True:
            nid = f"{first[0]}{last[0]}".lower() + f"{rng.randrange(10000):04d}"
            if nid not in used: used.add(nid); break
        mapping[netid.strip().lower()] = (nid, first, last)
        lines.append(f"   {yy.strip()}/{last}/{first}/{precept.strip()}/{nid}/{rng.randrange(100000000, 1000000000)}/")
    (out / "enroll.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, header in (("accommodations.txt", "netids of students taking the exam in the extra room (FAKE DATA)"),
                         ("lefty.txt", "netids of students who need a left-handed desk (FAKE DATA)")):
        rows = [f"# {header}"] + [f"{mapping[n][0]}    # {mapping[n][1]} {mapping[n][2]}" for n in read_ids(real / name)]
        (out / name).write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote fake data for {len(lines)} students -> {out}")

if __name__ == "__main__":
    main()

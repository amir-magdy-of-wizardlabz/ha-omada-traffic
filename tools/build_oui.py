#!/usr/bin/env python3
"""Build custom_components/omada_traffic/oui.tsv from the IEEE registry.

Usage: tools/build_oui.py path/to/oui.csv
Get the CSV from https://standards-oui.ieee.org/oui/oui.csv (public, a few MB).
"""
import csv
import pathlib
import sys

out = pathlib.Path(__file__).resolve().parent.parent / "custom_components/omada_traffic/oui.tsv"
rows = {}
with open(sys.argv[1], newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        prefix = r["Assignment"].strip().upper()
        name = " ".join(r["Organization Name"].split())
        if len(prefix) == 6 and name:
            rows[prefix] = name
out.write_text("".join(f"{p}\t{n}\n" for p, n in sorted(rows.items())), encoding="utf-8")
print(f"{len(rows)} prefixes -> {out}")

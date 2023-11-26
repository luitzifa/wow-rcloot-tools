#!/usr/bin/env python

import csv
import make_gsheet
import json

c = {}

with open("/home/dakr/Downloads/wishlist-export.csv", "r") as wl:
    dwl = csv.DictReader(wl)
    for row in dwl:
        if row["character_name"] not in c:
            c[row["character_name"]] = []
        item = make_gsheet.get_item_info(row["item_id"])
        item_name = item["wowhead"]["item"]["name"]
        item_lvl = item["wowhead"]["item"]["level"]
        item_slot = make_gsheet.get_item_slot(item)
        c[row["character_name"]].append((item_name, item_slot, item_lvl))

counter = {}
for p, s in c.items():
    counter[p] = {}
    for i in s:
        if i[1] not in counter[p]:
            counter[p][i[1]] = 1
        else:
            counter[p][i[1]] += 1

for p, s in counter.items():
    for i, l in s.items():
        if i in ["schmuck", "finger", "einhändig"] and l <= 4:
            continue
        elif l <= 2:
            continue
        print(f"{p}, {i}, {l}")

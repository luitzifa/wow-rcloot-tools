#!/usr/bin/env python

import csv
from pdb import set_trace
import click
import pygsheets
import requests
import xmltodict
import datetime
import json


def name(name):
    return name.split("-")[0]


def get_item_info(itemid):
    with open("item.cache", "r") as cache:
        try:
            itemcache = json.load(cache)
        except json.decoder.JSONDecodeError:
            itemcache = {}
    if itemid not in itemcache:
        r = requests.get(f"https://www.wowhead.com/de/item={itemid}&xml")
        itemcache[itemid] = xmltodict.parse(r.content)
        with open("item.cache", "w") as cache:
            cache.write(json.dumps(itemcache))
    return itemcache[itemid]


def get_item_slot(item):
    with open("itemslot_overwrite.json", "r") as db:
        slotdb = json.load(db)
    itemid = item["wowhead"]["item"]["@id"]
    name = item["wowhead"]["item"]["name"]
    orig_item_slot = item["wowhead"]["item"]["inventorySlot"].get("#text")
    if orig_item_slot == "In Schildhand geführt":
        orig_item_slot = "Schildhand"
    if "Buchband" in name:
        orig_item_slot = "Buchband"
    if "Götze" in name:
        orig_item_slot = "Götze"
    if "Totem" in name:
        orig_item_slot = "Totem"
    if "Siegel" in name:
        orig_item_slot = "Siegel"
    new_item_slot = slotdb.get(itemid)
    if new_item_slot:
        return new_item_slot.lower()
    if orig_item_slot:
        return orig_item_slot.lower()
    return "sonstige"


@click.command()
@click.option("--document", "-d", default="crush-loot")
@click.option("--title", "-t", default="Phase1")
@click.argument("cred_file", type=click.Path())
@click.argument("csvfiles", type=click.File(), nargs=-1)
def cli(document, title, cred_file, csvfiles):
    sheet_header_begin = [
        "Player",
        "Hardmode",
        "BiS",
        "Upgrade",
        "Offspec",
        "Roll",
        "Reason",
    ]
    sheet_header_end = [
        "Questitem",
        "Sonstige",
        "Last Item",
    ]
    recieved_types = {
        "Nebenspezialisierung": "offspec",
        "Hauptspezialisierung/Bedarf": "bis",
        "Verwürfelt": "roll",
        "Upgrade für Mainspec": "upgrade",
        "Hardmode": "hardmode",
    }
    overview_sheet_content = []
    item_sheet_content = []
    itemslots = [
        "Kopf",
        "Hals",
        "Schulter",
        "Rücken",
        "Brust",
        "Handgelenk",
        "Hände",
        "Taille",
        "Beine",
        "Füße",
        "Finger",
        "Schmuck",
        "Zweihändig",
        "Einhändig",
        "Schildhand",
    ]
    rtypes_of_interest = ["hardmode", "bis", "upgrade", "offspec"]
    char_loot = {}
    for file in csvfiles:
        loot = csv.DictReader(file)
        for row in loot:
            player = name(row["player"])
            if row["response"] not in recieved_types:
                continue

            if player not in char_loot:
                char_loot[player] = {}
                char_loot[player]["items"] = []
                char_loot[player]["hardmode"] = 0
                char_loot[player]["bis"] = 0
                char_loot[player]["upgrade"] = 0
                char_loot[player]["offspec"] = 0
                char_loot[player]["roll"] = 0

            rtype = recieved_types[row["response"]]
            char_loot[player][rtype] += 1

            item = get_item_info(row["itemID"])
            item_name = item["wowhead"]["item"]["name"]
            item_link = item["wowhead"]["item"]["link"]
            item_slot = get_item_slot(item)

            char_loot[player]["items"].append(
                (row["date"], rtype, item_slot, item_name, item_link)
            )

            known_slots = list([_.lower() for _ in itemslots + sheet_header_end])
            if item_slot.lower() not in known_slots:
                itemslots.append(item_slot.capitalize())

            if item_slot not in char_loot[player]:
                char_loot[player][item_slot] = dict((_, 0) for _ in rtypes_of_interest)
            if rtype in rtypes_of_interest:
                char_loot[player][item_slot][rtype] += 1

    overview_sheet_content.append(
        sheet_header_begin + list(itemslots) + sheet_header_end
    )
    item_sheet_content.append(["Player", "Date", "Reason", "Slot", "Item"])

    for player, v in sorted(char_loot.items()):
        v["items"].sort(
            key=lambda i: datetime.datetime.strptime(i[0], "%d.%m.%y"), reverse=True
        )

        rownumber = 0
        for rtype in rtypes_of_interest:
            if rownumber < 1:
                row = [player]
                # add main counter
                for head in sheet_header_begin[1:-1]:
                    row.append(v[head.lower()])
            else:
                row = [""] * (len(sheet_header_begin) - 1)

            row.append(rtype.capitalize()[0])

            for slot in itemslots + sheet_header_end[:-1]:
                content = v.get(slot.lower(), "")
                if isinstance(content, dict):
                    content = content[rtype]
                if content == 0:
                    content = ""
                row.append(content)

            for vitem in v["items"]:
                if vitem[1] == rtype:
                    row.append(
                        f'=HYPERLINK("{vitem[4]}";"{vitem[0]}: {vitem[3]} / {vitem[2]}")'
                    )
                    break
            overview_sheet_content.append(row)
            rownumber += 1
        for item in v["items"]:
            item_sheet_content.append(
                [
                    player,
                    item[0],
                    item[1].capitalize(),
                    item[2].capitalize(),
                    f'=HYPERLINK("{item[4]}";"{item[3]}")',
                ]
            )
    # import pdb

    # pdb.set_trace()
    client = pygsheets.authorize(service_account_file=cred_file)
    sh = client.open(document)
    wks_dummy = sh.add_worksheet("dummy")
    try:
        wks_overview = sh.worksheet_by_title(title)
        wks_items = sh.worksheet_by_title(f"{title}_items")
        sh.del_worksheet(wks_overview)
        sh.del_worksheet(wks_items)
    except:
        pass
    wks_overview = sh.add_worksheet(title)
    wks_items = sh.add_worksheet(f"{title}_items")
    sh.del_worksheet(wks_dummy)

    wks_overview.update_values("A1", overview_sheet_content)
    wks_items.update_values("A1", item_sheet_content)


if __name__ == "__main__":
    cli()

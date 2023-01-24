#!/usr/bin/env python

import csv
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
    if "Buchband" in name or "Götze" in name or "Totem" in name:
        orig_item_slot = "Distanz"
    new_item_slot = slotdb.get(itemid)
    if new_item_slot:
        return new_item_slot.lower()
    if orig_item_slot:
        return orig_item_slot.lower()
    return "sonstige"


@click.command()
@click.argument('cred_file', type=click.Path())
@click.argument('csvfiles', type=click.File(), nargs=-1)
def cli(cred_file, csvfiles):
    sheet_header_begin = ["Player", "Hardmode", "BiS", "Upgrade", "Offspec"]
    sheet_header_end = ["Questitem", "Sonstige", "Roll", "Items"]
    recieved_types = {
        "Nebenspezialisierung": "offspec",
        "Hauptspezialisierung/Bedarf": "bis",
        "Verwürfelt": "roll",
        "Upgrade für Mainspec": "upgrade",
        "Hardmode": "hardmode"
    }
    sheet_content = []
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
            
            char_loot[player]["items"].append((row['date'], rtype, item_slot, item_name, item_link))
            
            if rtype not in ["bis", "hardmode"]:
                continue
            
            known_slots = list([_.lower() for _ in itemslots + sheet_header_end])
            if item_slot.lower() not in known_slots:
                itemslots.append(item_slot.capitalize())
            if item_slot not in char_loot[player]:
                char_loot[player][item_slot] = 1
            else:
                char_loot[player][item_slot] += 1

    sheet_content.append(
        sheet_header_begin +
        list(itemslots) +
        sheet_header_end
    )

    for player, v in char_loot.items():
        row = [player]
        for head in sheet_header_begin[1:]:
            row.append(v[head.lower()])
        for slot in itemslots:
            row.append(v.get(slot.lower(), ""))
        for head in sheet_header_end[:-1]:
            row.append(v.get(head.lower(), ""))
        
        v["items"].sort(key=lambda i: datetime.datetime.strptime(i[0], "%d.%m.%y"), reverse=True)
        row += [f'=HYPERLINK("{_[4]}";"{_[0]} ({_[1]}): {_[3]}/{_[2]}")' for _ in v["items"]]
        
        sheet_content.append(row)
    
    client = pygsheets.authorize(service_account_file=cred_file)    
    sh = client.open('crush-loot')
    wks = sh.sheet1
    wks.clear()
    wks.update_values('A1', sheet_content)
    

if __name__ == '__main__':
    cli()

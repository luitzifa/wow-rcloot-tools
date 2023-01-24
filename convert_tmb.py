import pathlib

filter_items = ["43346", "43345", "43954", "37254"]
filter_offspec = ["Nebenspezialisierung"]
filter_type = ["Entzaubern", "Bankfach"]
filter_offspec_lines = []
filter_item_lines = []
full_history = []
str_rep = [("âsphaar-Razorfen","Âsphaar-Razorfen"),]
headerline = "player,date,time,id,item,itemID,itemString,response,votes,class,instance,boss,difficultyID,mapID,groupSize,gear1,gear2,responseID,isAwardReason,subType,equipLoc,note,owner"

def search_filter(filter, line):
    for filter_item in filter:
        if f",{filter_item}," in line:
            return True
    return False

def slashfy_line(line):
    lines = line.split(",")
    lines[1] = lines[1].replace(".", "/")
    return ",".join(lines)     

for raw_file in pathlib.Path(".").glob("*_raw.txt"):
    file = pathlib.Path(raw_file)
    basename = file.stem
    with open(file, 'r', encoding='utf8') as cf:
        content = cf.read()
    filename = basename + "_clean_{}.txt"

    with open(filename.format("DE"), "w", encoding='utf8') as fde, open(filename.format("EN"), "w", encoding='utf8') as fen:
        for line in content.splitlines():
            for old_str, new_str in str_rep:
                if old_str in line:
                    line = line.replace(old_str, new_str)
            if search_filter(filter_items ,line):
                filter_item_lines.append(line)
            elif search_filter(filter_type, line):
                continue
            elif search_filter(filter_offspec, line):
                filter_offspec_lines.append(line)
                continue
            full_history.append(line)
            fde.write(line + "\n")
            fen.write(slashfy_line(line) + "\n")

roll_fn = "roll_recipients_{}.txt"
with open(roll_fn.format("DE"), "w", encoding='utf8') as fde, open(roll_fn.format("EN"), "w", encoding='utf8') as fen:
    fde.write(headerline + "\n")
    fen.write(headerline + "\n")
    for line in filter_item_lines:
        fde.write(line + "\n")
        fen.write(slashfy_line(line) + "\n")

roll_fn = "offspec_recipients_{}.txt"
with open(roll_fn.format("DE"), "w", encoding='utf8') as fde, open(roll_fn.format("EN"), "w", encoding='utf8') as fen:
    fde.write(headerline + "\n")
    fen.write(headerline + "\n")
    for line in filter_offspec_lines:
        fde.write(line + "\n")
        fen.write(slashfy_line(line) + "\n")

all_fn = "loot_all_clean_{}.txt"
with open(all_fn.format("DE"), "w", encoding='utf8') as fde, open(all_fn.format("EN"), "w", encoding='utf8') as fen:
    fde.write(headerline + "\n")
    fen.write(headerline + "\n")
    for line in full_history:
        if line == headerline:
            continue
        fde.write(line + "\n")
        fen.write(slashfy_line(line) + "\n")

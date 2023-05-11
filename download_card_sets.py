import requests
import json
from pathlib import Path
import os
import shutil

CARD_SET_FOLDER = "card_sets"
SET_NAME_TEMPLATES = ["set{}", "set{}cde"]

def delete_card_sets():
    print("deleting folder ", CARD_SET_FOLDER)
    try:
        shutil.rmtree(CARD_SET_FOLDER)
    except:
        print(f"Folder '{CARD_SET_FOLDER}' not found, skipping delete...")

def download_missing_card_sets():
    if not os.path.isdir("card_sets"):  # Entire folder is missing -> create one
        os.mkdir("card_sets")
    (_, _, card_set_files) = next(os.walk("card_sets"))
    curr_sets_nums = set(map(lambda card_set: int(card_set[3]), card_set_files))
    set_num = len(curr_sets_nums)
    for s in range(1, max(curr_sets_nums) if curr_sets_nums else 1):
        if s not in curr_sets_nums:
            set_num += get_card_set(s)

    counter = 1
    while get_card_set(set_num + counter):
        counter += 1


def get_card_set(set_number):
    set_downloaded = False

    for set_name_template in SET_NAME_TEMPLATES:
        set_downloaded = get_card_set_and_extract(set_name_template.format(set_number)) or set_downloaded

    return set_downloaded


def get_card_set_and_extract(name) -> bool:
    card_set = download_card_set(f"https://dd.b.pvp.net/latest/{name}/en_us/data/{name}-en_us.json")
    if card_set is None:
        return False
 
    base_dir = Path("card_sets")
    base_dir.mkdir(exist_ok=True)

    card_set_path = base_dir / (f"{name}.json")

    card_set_json = json.loads(card_set)
    card_set_path.write_text(json.dumps(card_set_json, indent=2))

    print("downloaded card set:", name)

    return True


def download_card_set(url):
    res = requests.get(url)
    if not res.ok:  # File does not exist
        return None
    return res.content
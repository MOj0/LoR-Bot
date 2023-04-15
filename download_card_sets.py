import requests
import zipfile
import io
import os
import shutil


def is_card_set_missing():
    if not os.path.isdir("card_sets"):  # Card sets are missing
        return True
    (_, _, card_set_files) = next(os.walk("card_sets"))
    n_sets = len(card_set_files)
    curr_sets_nums = tuple(map(lambda card_set: int(card_set[3]), card_set_files))
    if any(s not in curr_sets_nums for s in range(1, n_sets + 1)):
        return True

    next_set = "set" + str(n_sets + 1) + "-lite-en_us"
    zip_file_url = "https://dd.b.pvp.net/latest/" + next_set + ".zip"
    r = requests.get(zip_file_url, stream=True)
    return r.ok


def download_missing_card_sets():
    if not os.path.isdir("card_sets"):  # Entire folder is missing -> create one
        os.mkdir("card_sets")
    (_, _, card_set_files) = next(os.walk("card_sets"))
    curr_sets_nums = set(map(lambda card_set: int(card_set[3]), card_set_files))
    n_sets = len(curr_sets_nums)
    for s in range(1, max(curr_sets_nums) if curr_sets_nums else 1):
        if s not in curr_sets_nums:
            n_sets += get_card_set(s)

    counter = 1
    while get_card_set(n_sets + counter):
        counter += 1


def get_card_set(set_number):
    set = f"set{set_number}"
    set_cde = f"set{set_number}cde"

    set_downloaded = get_card_set_and_extract(set)
    set_cde_downloaded = get_card_set_and_extract(set_cde)

    return set_downloaded or set_cde_downloaded


def get_card_set_and_extract(name):
    card_set = download_card_set(f"https://dd.b.pvp.net/latest/{name}-lite-en_us.zip")
    if card_set is None:
        return False

    set_path = f"en_us/data/{name}-en_us.json"
    set_dest = f"./card_sets/{name}"
    card_set.extract(set_path, set_dest)

    cwd = os.getcwd()
    source = f"{cwd}\\card_sets\\{name}\\en_us\\data\\{name}-en_us.json"
    dest = f"{cwd}\\card_sets\\{name}.json"

    shutil.move(source, dest)
    shutil.rmtree(set_dest)

    print("downloaded card set:", name)

    return True


def download_card_set(url):
    res = requests.get(url, stream=True)
    if not res.ok:  # File does not exist
        return None
    return zipfile.ZipFile(io.BytesIO(res.content))

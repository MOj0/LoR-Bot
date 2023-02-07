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
    curr_sets_nums = tuple(map(lambda card_set: int(card_set[3]), card_set_files))
    n_sets = len(card_set_files)
    for s in range(1, max(curr_sets_nums) if curr_sets_nums else 1):
        if s not in curr_sets_nums:
            n_sets += download_card_set(s)

    counter = 1
    while download_card_set(n_sets + counter):
        counter += 1


def download_card_set(set_number):
    next_set = "set" + str(set_number) + "-en_us"
    next_set_lite = "set" + str(set_number) + "-lite-en_us"

    zip_file_url = "https://dd.b.pvp.net/latest/" + next_set_lite + ".zip"
    r = requests.get(zip_file_url, stream=True)
    if not r.ok:  # File does not exist -> done
        return False
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extract("en_us/data/" + next_set + ".json", "./card_sets/"+next_set)

    cwd = os.getcwd()
    shutil.move(cwd + "\\card_sets\\" + next_set + "\\en_us\\data\\" + next_set +
                ".json", cwd + "\\card_sets\\" + next_set + ".json")
    shutil.rmtree("./card_sets/" + next_set)

    return True

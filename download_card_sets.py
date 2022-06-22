import requests
import zipfile
import io
import os
import shutil

def is_card_set_missing():
    (_, _, card_set_files) = next(os.walk("card_sets"))
    n_sets = len(card_set_files)
    next_set = "set" + str(n_sets + 1) + "-en_us"
    zip_file_url = "https://dd.b.pvp.net/latest/" + next_set + ".zip"
    r = requests.get(zip_file_url, stream=True)
    return r.ok

def download_missing_card_sets():
    (_, _, card_set_files) = next(os.walk("card_sets"))
    n_sets = len(card_set_files) # FIXME: If card set 3 is missing and others are present (1, 2, _, 4, ...) -> BUG
    counter = 1
    cwd = os.getcwd()

    while True:
        next_set = "set" + str(n_sets + counter) + "-en_us"

        zip_file_url = "https://dd.b.pvp.net/latest/" + next_set + ".zip"
        r = requests.get(zip_file_url, stream=True)
        if not r.ok:  # File does not exist -> done
            break
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extract("en_us/data/" + next_set + ".json", "./card_sets/"+next_set)

        shutil.move(cwd + "\\card_sets\\" + next_set + "\\en_us\\data\\" + next_set +
                    ".json", cwd + "\\card_sets\\" + next_set + ".json")
        shutil.rmtree("./card_sets/" + next_set)

        counter += 1

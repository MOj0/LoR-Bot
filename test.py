import concurrent.futures
import urllib.request
import json
from time import sleep


# URLS = ['http://www.foxnews.com/',
#         'http://www.cnn.com/',
#         'http://europe.wsj.com/',
#         'http://www.bbc.co.uk/',
#         'http://some-made-up-domain.com/']

URLS = ["http://127.0.0.1:21337/positional-rectangles"]
# GAME_DATA_LINK = "http://127.0.0.1:21337/positional-rectangles"
# DECK_LINK = "http://127.0.0.1:21337/static-decklist"
# GAME_RESULT_LINK = "http://127.0.0.1:21337/game-result"

# Retrieve a single page and report the URL and contents
def load_url(url):
    with urllib.request.urlopen(url) as conn:
        return json.loads(conn.read().decode())


# We can use a with statement to ensure threads are cleaned up promptly
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    count = 0
    while True:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(load_url, url): url for url in URLS}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
            else:
                print(count, url, "contains:", data)
                count += 1
        sleep(1)

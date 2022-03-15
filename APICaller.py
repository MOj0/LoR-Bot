import urllib.request
import json
from time import sleep

class APICaller:
    def __init__(self):
        self.game_data_link = "http://127.0.0.1:21337/positional-rectangles"
        self.game_data = {}
        self.deck_link = "http://127.0.0.1:21337/static-decklist"
        self.cards_data = {}
        self.game_result_link = "http://127.0.0.1:21337/game-result"
        self.game_result = {}

    def call_api(self):
        while True:
            game_url = urllib.request.urlopen(self.game_data_link)
            self.game_data = json.loads(game_url.read().decode())

            deck_url = urllib.request.urlopen(self.deck_link)
            self.cards_data = json.loads(deck_url.read().decode())

            game_result = urllib.request.urlopen(self.game_result_link)
            self.game_result = json.loads(game_result.read().decode())

            sleep(1)

    def get_game_data(self):
        return self.game_data

    def get_cards_data(self):
        return self.cards_data

    def get_game_result(self):
        return self.game_result

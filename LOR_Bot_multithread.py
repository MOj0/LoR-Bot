import masks
import numpy as np
import cv2
from PIL import ImageGrab
import win32api
import win32con
import time
import keyboard
import win32gui
from termcolor import colored
import urllib.request
import json
from collections import defaultdict
import os
import threading


# CLASSES
class Card:
    def __init__(self, name, cost, attack, health, type, keywords):
        self.name = name
        self.cost = cost
        self.attack = attack
        self.health = health
        self.type = type
        self.keywords = keywords

    def __str__(self):
        return "Card({} ({}) T: {} A: {} H: {})".format(self.name, self.cost, self.type, self.attack, self.health)

    def get_name(self):
        return self.name

    def is_spell(self):
        return self.type == "Spell"


class InGameCard(Card):
    def __init__(self, card, x, y, w, h, is_local):
        super().__init__(card.name, card.cost, card.attack, card.health, card.type, card.keywords)
        self.top_center = (int(x + w / 2), int(y - h / 4))
        self.is_local = is_local

    def __str__(self):
        return "InGameCard({} -- top_center:({}); is_local:{})".format(super().__str__(), self.top_center, self.is_local)

    def get_pos(self):
        return self.top_center


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

            time.sleep(1)

    def get_game_data(self):
        return self.game_data

    def get_cards_data(self):
        return self.cards_data

    def get_game_result(self):
        return self.game_result


# FUNCTIONS
def update_window_info(handle, window):
    if win32gui.GetWindowText(handle) == "Legends of Runeterra":
        rect = win32gui.GetWindowRect(handle)
        for i, r in enumerate(rect):
            window[i] = r


def get_board_state(game_data, window_height) -> defaultdict:
    board_state = defaultdict(list)
    if not game_data:
        return board_state

    for in_game_card in game_data["Rectangles"]:
        card_code = in_game_card["CardCode"]
        if card_code == "face":
            continue

        c = ALL_CARDS[card_code]
        x = in_game_card["TopLeftX"]
        y = in_game_card["TopLeftY"]
        w = in_game_card["Width"]
        h = in_game_card["Height"]
        local_player = in_game_card["LocalPlayer"]
        in_game_card_obj = InGameCard(c, x, y, w, h, local_player)

        card_y = window_height - in_game_card_obj.top_center[1]
        ratio = card_y / window_height
        if ratio > 0.97:
            board_state["cards_hand"].append(in_game_card_obj)
        elif ratio > 0.75:
            board_state["cards_board"].append(in_game_card_obj)
        elif ratio > 0.6:
            board_state["cards_attk"].append(in_game_card_obj)
        elif ratio > 0.45:
            board_state["spell_stack"].append(in_game_card_obj)
        elif ratio > 0.275:
            board_state["opponent_cards_attk"].append(in_game_card_obj)
        elif ratio > 0.1:
            board_state["opponent_cards_board"].append(in_game_card_obj)
        else:
            board_state["opponent_cards_hand"].append(in_game_card_obj)

        # # Draw circle in the top center of cards
        # screen = cv2.circle(screen, (circle_x, circle_y), 20, (255, 0, 0), 2)
        # screen = cv2.putText(screen, str(round(ratio, 3)), (circle_x - 45, circle_y - 30), font, 1, (0, 255, 0), 2)

    return board_state


def get_game_state(board_state, window_width, window_height, frames, image, attack_token_bounds) -> str:
    if not game_data or game_data["GameState"] == "Menus":
        return "Menus"
    # Mulligan check
    for in_game_card in game_data["Rectangles"]:
        card_code = in_game_card["CardCode"]
        if card_code == "face":
            continue

        c = ALL_CARDS[card_code]
        x = in_game_card["TopLeftX"]
        y = in_game_card["TopLeftY"]
        w = in_game_card["Width"]
        h = in_game_card["Height"]
        local_player = in_game_card["LocalPlayer"]
        in_game_card_obj = InGameCard(c, x, y, w, h, local_player)

        circle_y = window_height - in_game_card_obj.top_center[1]
        if not local_player or not(circle_y < window_height / 2):
            break
    else:
        return "Mulligan"

    if len(board_state["opponent_cards_attk"]):
        return "Blocking"

    # Check if its our turn
    turn_btn_sub_img = np.array(image.crop(box=(int(window_width * 0.77), int(window_height *
                                0.42), int(window_width * 0.93), int(window_height * 0.58))))
    hsv = cv2.cvtColor(turn_btn_sub_img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (5, 200, 200), (15, 255, 255))  # Blue color space
    target = cv2.cvtColor(cv2.bitwise_and(turn_btn_sub_img, turn_btn_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
    # cv2.imshow("BLUE turn button end check", target)
    if cv2.countNonZero(target) < 100:  # End turn button is GRAY
        return "Opponent_Turn"

    # Check if local_player has the attack token
    attack_token_bound_l_x = int(window_width * attack_token_bounds[0][0])
    attack_token_bound_l_y = int(window_height * attack_token_bounds[0][1])
    attack_token_bound_r_x = int(window_width * attack_token_bounds[1][0])
    attack_token_bound_r_y = int(window_height * attack_token_bounds[1][1])
    for img in frames:
        attack_token_sub_img = np.array(img.crop(
            box=(attack_token_bound_l_x, attack_token_bound_l_y, attack_token_bound_r_x, attack_token_bound_r_y)))
        hsv = cv2.cvtColor(attack_token_sub_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (100, 192, 160), (120, 255, 255))  # Orange
        target = cv2.cvtColor(cv2.bitwise_and(attack_token_sub_img,
                              attack_token_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
        # cv2.imshow("attack token check", target)
        num_orange_px = cv2.countNonZero(target)
        if num_orange_px <= 10:  # Not enough orange pixels for attack token
            break
    else:
        return "Attack_Turn"

    return "Defend_Turn"


def get_mana(frames):
    # mana_vals = []
    # for image in frames:
    #     mana_edges = cv2.Canny(cv2.cvtColor(
    #         np.array(image.crop(box=(1585, 638, 1635, 675))), cv2.COLOR_BGR2GRAY), 100, 100)

    #     for i, mask in enumerate(MANA_MASKS):
    #         num_match_px = sum(map(bool, (val for edge, msk in zip(mana_edges, mask) for val in edge[msk])))
    #         match_rate = num_match_px / NUM_PX_MASK[i]
    #         if match_rate > 0.95:
    #             mana_vals.append(i)
    #             break

    # Show frame
    # if mana_vals and mana_vals.count(mana_vals[0]) == len(mana_vals):
    #     mana_number = cv2.putText(mana_number, "{}".format(mana_vals[0]), (0, 20), font, 1, (255, 255, 255), 2)
    #     cv2.imshow("mana_label", mana_number)

    # Magic
    mana_vals = tuple(i for image in frames for i, mask in enumerate(MANA_MASKS) if sum(map(bool, (val for edge, msk in zip(cv2.Canny(cv2.cvtColor(
        np.array(image.crop(box=(1585, 638, 1635, 675))), cv2.COLOR_BGR2GRAY), 100, 100), mask) for val in edge[msk]))) / NUM_PX_MASK[i] > 0.95)

    return mana_vals[0] if mana_vals else -1


# INIT
font = cv2.FONT_HERSHEY_SIMPLEX
font_color = (0, 0, 255)
window_info = [-1, -1, -1, -1]  # [location, size]
attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
game_state = ""
prev_game_state = ""
mana = 1
prev_mana = 1
spell_mana = 0
turn = 1
games_won = 0
n_games = 0
first_pass_blocking = False
deck_type = None  # Ephemeral, Aggro
block_counter = 0

# Cards parsing
(_, _, CARD_SET_FILES) = next(os.walk("card_sets"))
cards_data = []
for card_set in CARD_SET_FILES:
    cards_data += json.load(open("card_sets/"+card_set, encoding="utf8"))

ALL_CARDS = {card["cardCode"]: Card(card["name"], card["cost"], card["attack"],
                                    card["health"], card["type"], card["keywords"]) for card in cards_data}

MANA_MASKS = (masks.ZERO, masks.ONE, masks.TWO, masks.THREE, masks.FOUR,
              masks.FIVE, masks.SIX, masks.SEVEN, masks.EIGHT, masks.NINE, masks.TEN)
NUM_PX_MASK = tuple(sum(val for line in mask for val in line) for mask in MANA_MASKS)

# MAIN
win32gui.EnumWindows(update_window_info, window_info)
if window_info == [-1, -1, -1, -1]:
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)

api_caller = APICaller()
api_thread = threading.Thread(target=api_caller.call_api)
api_thread.daemon = True
api_thread.start()

while True:
    # Get window data
    win32gui.EnumWindows(update_window_info, window_info)
    window_x, window_y, window_width, window_height = window_info[0], window_info[1], window_info[2] - \
        window_info[0], window_info[3] - window_info[1]

    # 4 frames are needed becuase of mana recognition!
    frames = [ImageGrab.grab(bbox=(window_x, window_y, window_x + window_width, window_y +
                             window_height), all_screens=True) for _ in range(4)]
    image = frames[-1]
    screen = np.array(image)

    game_data = api_caller.get_game_data()
    board_state = get_board_state(game_data, window_height)
    game_state = "(HOLD)" if keyboard.is_pressed("ctrl") else get_game_state(
        board_state, window_width, window_height, frames, image, attack_token_bounds)
    mana = get_mana(frames)

    shape = (720, 1280)
    background_color = (0.0, 0.4, 0.1) if game_state == "(HOLD)" else (0.0, 0.0, 0.0)
    board_state_img = np.full((*shape, len(background_color)), background_color)
    board_state_img = cv2.putText(board_state_img, deck_type, (500, 100), font, 1, (255, 255, 255), 2)
    board_state_img = cv2.putText(board_state_img, "{}".format(game_state), (1000, 40), font, 1, (0, 255, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Round {}".format(turn), (1000, 80), font, 1, (0, 255, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Mana {}".format(mana), (1000, 120), font, 1, (0, 20, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Spell mana {}".format(spell_mana),
                                  (1000, 160), font, 1, (0, 100, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Prev mana {}".format(prev_mana),
                                  (1000, 200), font, 1, (0, 100, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Win% {}/{} ({})".format(
        games_won, n_games, ("/" if n_games == 0 else str(games_won / n_games)) + " %"),
        (1000, 240), font, 1, (0, 255, 255), 2)

    for i, (position, cards) in enumerate(board_state.items()):
        board_state_img = cv2.putText(board_state_img, position, (20, 30 + 150 * i), font, 1, (0, 255, 0), 2)
        for j, card in enumerate(cards):
            board_state_img = cv2.putText(board_state_img, card.get_name(),
                                          (20, 50 + 150 * i + 25 * j), font, 1, (255, 0, 0), 2)

    # Show board state
    cv2.imshow('Board state', board_state_img)

    # Quit condition
    if cv2.waitKey(20) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break

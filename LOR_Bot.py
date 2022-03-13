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


# FUNCTIONS


def window_callback(handle, window):
    if win32gui.GetWindowText(handle) == "Legends of Runeterra":
        rect = win32gui.GetWindowRect(handle)
        for i, r in enumerate(rect):
            window[i] = r


def click(pos, y=None):
    if y is not None:
        x = pos
    else:
        (x, y) = pos

    (x, y) = (int(x), int(y))

    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def hold(pos, y=None):
    if y is not None:
        x = pos
    else:
        (x, y) = pos
    win32api.SetCursorPos((x, y))
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)


def release(pos, y=None):
    if y is not None:
        x = pos
    else:
        (x, y) = pos
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def select_deck(is_vs_ai=False):
    vals_ai = [(0.04721, 0.33454), (0.15738, 0.33401), (0.33180, 0.30779), (0.83213, 0.89538)]
    vals_pvp = [(0.04721, 0.33454), (0.15738, 0.25), (0.33180, 0.30779), (0.83213, 0.89538)]
    vals = vals_ai if is_vs_ai else vals_pvp
    for val in vals:
        v = (window_info[0] + val[0] * window_width, window_info[1] + val[1] * window_height)
        click(int(v[0]), int(v[1]))
        time.sleep(0.7)


def get_board_state(game_data):
    board_state = defaultdict(list)
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

        # Draw circle in the top center of cards
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

        # screen = cv2.circle(screen, (circle_x, circle_y), 20, (255, 0, 0), 2)
        # screen = cv2.putText(screen, str(round(ratio, 3)), (circle_x - 45, circle_y - 30), font, 1, (0, 255, 0), 2)

    # print(board_state.keys())
    return board_state


def get_game_state(board_state) -> str:
    if game_data["GameState"] == "Menus":
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
    cv2.imshow("BLUE turn button end check", target)
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
        cv2.imshow("attack token check", target)
        num_orange_px = cv2.countNonZero(target)
        if num_orange_px <= 10:  # Not enough orange pixels for attack token
            break
    else:
        return "Attack_Turn"

    return "Defend_Turn"


def get_mana():
    mana_vals = []
    for image in frames:
        mana_number = np.array(image.crop(box=(1585, 638, 1635, 675)))
        mana_number = cv2.cvtColor(mana_number, cv2.COLOR_BGR2GRAY)
        mana_edges = cv2.Canny(mana_number, 100, 100)

        for i, mask in enumerate(MANA_MASKS):
            num_mask_px = sum((val for line in mask for val in line))
            num_match_px = sum(map(bool, (val for e, z in zip(mana_edges, mask) for val in e[z])))
            match_rate = num_match_px / num_mask_px
            if match_rate > 0.95:
                mana_vals.append(i)
                break

    if mana_vals and mana_vals.count(mana_vals[0]) == len(mana_vals):
        mana_number = cv2.putText(mana_number, "{}".format(mana_vals[0]), (0, 20), font, 1, (255, 255, 255), 2)
        cv2.imshow("mana_label", mana_number)

    return mana_vals[0] if mana_vals else -1


def play_card(playable_card):
    (x, y) = (window_x + playable_card.top_center[0], window_y + window_height - playable_card.top_center[1])
    print("Playing at: ", x, y)
    hold(x, y)
    for i in range(3):
        time.sleep(0.5)
        win32api.SetCursorPos((x, int(y - window_height / 7 * i)))
    time.sleep(0.3)
    release(x, int(y - 3 * window_height / 7))
    time.sleep(0.3)
    if playable_card.is_spell():
        time.sleep(1)
        keyboard.send("space")


def drag_card_from_to(pos_src, pos_dest):
    pos_src = (window_x + pos_src[0], window_y + window_height - pos_src[1])
    pos_dest = (window_x + pos_dest[0], window_y + window_height - pos_dest[1])
    hold(pos_src)
    time.sleep(0.3)
    win32api.SetCursorPos(((pos_src[0] + pos_dest[0]) // 2, (pos_src[1] + pos_dest[1]) // 2))
    time.sleep(1)
    release(pos_dest)
    time.sleep(0.5)


def blocked_with(blocking_card, enemy_cards, ally_cards):
    for enemy_card in enemy_cards:
        if "Elusive" in enemy_card.keywords:
            continue
        is_blockable = True
        if "Ephemeral" in blocking_card.keywords or enemy_card.attack < blocking_card.health:  # Defensive block
            # if "Ephemeral" in blocking_card.keywords or enemy_card.health <= blocking_card.attack:  # Aggressive block
            for ally_card in ally_cards:  # Check if card is already blocked or elusive
                if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                    is_blockable = False
                    break

            if is_blockable:
                drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                return True
    return False


def continue_and_replay():
    time.sleep(4)
    continue_btn_pos = (window_x + 0.66 * window_width, window_y + window_height * 0.90)
    for _ in range(4):
        click(continue_btn_pos)
        time.sleep(1.5)
    time.sleep(1)


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


# INIT
font = cv2.FONT_HERSHEY_SIMPLEX
font_color = (0, 0, 255)
window_info = [-1, -1, -1, -1]  # [location, size]

turn_btn_pos = (0.86356, 0.54873)
attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
turn_btn_bounds = ((0.8, 0.45), (0.99, 0.6))
attack_token_count = []  # If 4 values are > 10, we are on the attack turn
# OPTIONS: Menus, InProgress(Mulligan, Opponent_Turn, Defend_Turn, Attack_Turn, Attacking, Blocking, Round_End, Pass), (HOLD)
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

GAME_DATA_LINK = "http://127.0.0.1:21337/positional-rectangles"
DECK_LINK = "http://127.0.0.1:21337/static-decklist"
GAME_RESULT_LINK = "http://127.0.0.1:21337/game-result"

MANA_MASKS = [masks.ZERO, masks.ONE, masks.TWO, masks.THREE, masks.FOUR,
              masks.FIVE, masks.SIX, masks.SEVEN, masks.EIGHT, masks.NINE, masks.TEN]

# NOTE Mana discounts, Buffs, Debuffs are NOT accounted for (static decklist)!
# NOTE Values for mana checking are hardcoded, only works fullscreen (1920x1080)!


# MAIN
win32gui.EnumWindows(window_callback, window_info)
if window_info == [-1, -1, -1, -1]:
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)

game_id = int(json.loads(urllib.request.urlopen(GAME_RESULT_LINK).read().decode())["GameID"])
prev_game_id = game_id

while (True):
    game_result = json.loads(urllib.request.urlopen(GAME_RESULT_LINK).read().decode())
    game_id = int(game_result["GameID"])
    if game_id > prev_game_id:  # Game is finished
        print("Game ended... waiting for animations")
        time.sleep(20)

        continue_and_replay()

        games_won += 1 if game_result["LocalPlayerWon"] == "true" else 0
        n_games += 1
        prev_game_id = game_id
        continue

    # Get window data
    win32gui.EnumWindows(window_callback, window_info)  # Updates the window_info

    game_url = urllib.request.urlopen(GAME_DATA_LINK)
    game_data = json.loads(game_url.read().decode())
    # print(game_data)

    # # Window Handle + game_data info # NOTE Deprecated
    # window_x, window_y, window_width, window_height = (window_info[0], window_info[1], game_data["Screen"]
    #                                                    ["ScreenWidth"], game_data["Screen"]["ScreenHeight"])

    # Window Handle info
    window_x, window_y, window_width, window_height = window_info[0], window_info[1], window_info[2] - \
        window_info[0], window_info[3] - window_info[1]

    frames = [ImageGrab.grab(bbox=(window_x, window_y, window_x + window_width, window_y +
                             window_height), all_screens=True) for _ in range(4)]
    image = frames[-1]
    screen = np.array(image)

    prev_game_state = game_state
    board_state = get_board_state(game_data)
    game_state = "(HOLD)" if keyboard.is_pressed("ctrl") else get_game_state(board_state)

    if game_state == "(HOLD)":
        time.sleep(1)
        continue
    if game_state == "Menus":
        print("SELECTING DECK NOW!")
        select_deck(is_vs_ai=False)
        time.sleep(5)
        prev_game_state = game_state
        continue
    if game_state == "Mulligan" and prev_game_state == "Menus":  # Double-check so we don't get False Positives!
        print("Thinking...")
        time.sleep(7)
        prev_game_state = game_state
        continue

    mana = get_mana()
    if mana == -1:
        print("Unknown mana...")
        time.sleep(1.5)
        continue
    if mana > turn:  # New turn
        spell_mana = min(spell_mana + prev_mana, 3)
        turn = mana
        prev_mana = mana
        first_pass_blocking = False
        block_counter = 0

    # Get deck
    deck_url = urllib.request.urlopen(DECK_LINK)
    cards_data = json.loads(deck_url.read().decode())
    deck = [ALL_CARDS[cardCode] for cardCode, num_cards in cards_data["CardsInDeck"].items()
            for _ in range(num_cards)]
    for card in deck:
        if "Ephemeral" in card.keywords:
            deck_type = "Ephemeral"
            break
    else:
        deck_type = "Aggro"

    # Get cards in game
    in_game_cards = [card for cards in board_state.values() for card in cards]

    board_state_img = np.zeros((720, 1280, 3), np.uint8)
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
        for j, c in enumerate(cards):
            board_state_img = cv2.putText(board_state_img, c.get_name(),
                                          (20, 50 + 150 * i + 25 * j), font, 1, (255, 0, 0), 2)

    if game_state == "Mulligan":
        # Reset variables
        mana = prev_mana = turn = 1
        spell_mana = 0
        block_counter = 0

        # Mulligan
        for in_game_card_obj in in_game_cards:
            if in_game_card_obj.cost > 3:
                cx = window_x + in_game_card_obj.top_center[0]
                cy = window_y + window_height - in_game_card_obj.top_center[1]
                print("Cost greater than 3, clicking at", cx, cy)
                click(cx, cy)
                time.sleep(0.5)
        print("Confirming mulligan")
        click(window_x + window_width * turn_btn_pos[0], window_y + window_height * turn_btn_pos[1])
    elif game_state == "Opponent_Turn":
        time.sleep(1)
        continue
    elif game_state == "Blocking":
        if not first_pass_blocking:
            first_pass_blocking = True
            print("first blocking pass...")
            time.sleep(3)
            continue

        for i, blocking_card in enumerate(board_state["cards_board"]):
            if i < block_counter or blocking_card.get_name() == "Zed" or "Can't Block" in blocking_card.keywords:
                continue
            if blocked_with(blocking_card, board_state["opponent_cards_attk"], board_state["cards_attk"]):
                block_counter = (block_counter + 1) % len(board_state["cards_board"])
                break
        else:
            block_counter = 0
            keyboard.send("space")
    elif game_state == "Defend_Turn" or game_state == "Attack_Turn":
        if len(board_state["spell_stack"]) != 0 and all(card.is_spell() for card in board_state["spell_stack"]):
            keyboard.send("space")
            time.sleep(0.5)
        playable_cards = sorted(filter(lambda card: card.get_name() != "Shadowshift" and card.cost <= mana or card.is_spell()
                                       and card.cost <= mana + spell_mana, board_state["cards_hand"]), key=lambda card: card.cost, reverse=True)
        if len(playable_cards) == 0 and game_state == "Attack_Turn" or len(board_state["cards_board"]) == 6:
            keyboard.send("a")
            time.sleep(1.25)
            keyboard.send("space")
        else:
            for playable_card_in_hand in playable_cards:
                if deck_type == "Ephemeral" and (game_state == "Attack_Turn" and ("Ephemeral" in playable_card_in_hand.keywords or playable_card_in_hand.get_name() in ("Zed", "Hecarim", "Commander Ledros") or playable_card_in_hand.is_spell())
                                                 or game_state == "Defend_Turn" and "Ephemeral" not in playable_card_in_hand.keywords and not playable_card_in_hand.is_spell()) \
                        or deck_type == "Aggro":
                    print("Playing card: ", playable_card_in_hand)
                    play_card(playable_card_in_hand)
                    diff = playable_card_in_hand.cost
                    if playable_card_in_hand.is_spell():
                        diff = max(0, playable_card_in_hand.cost - spell_mana)
                        spell_mana = max(0, spell_mana - playable_card_in_hand.cost)
                    mana -= diff
                    prev_mana = mana
                    break
            else:
                if game_state == "Attack_Turn":
                    keyboard.send("a")
                    time.sleep(1.25)
                keyboard.send("space")
                time.sleep(2)

    # DRAW + CV stuff
    screen = cv2.putText(screen, game_state, (25, 100), font, 1, (0, 0, 255), 2)  # Draw game state

    # Mouse position (relative to window)
    mousePosText = str(win32api.GetCursorPos()[0]) + \
        ", " + str(win32api.GetCursorPos()[1])
    screen = cv2.putText(screen, mousePosText, (25, 150), font, 1, (0, 255, 0), 2)

    # # Mouse position (percentage)
    # mousePosText = "{:.5f}".format((win32api.GetCursorPos()[0] - window_info[0]) / window_width) + \
    #     ", " + "{:.5f}".format((win32api.GetCursorPos()[1] - window_info[1]) / window_height)
    # screen = cv2.putText(screen, mousePosText, (25, 150), font, 1, (0, 255, 0), 2)

    screen = cv2.putText(screen, "Turn {}".format(turn), (25, 200), font, 1, (0, 255, 255), 2)
    screen = cv2.putText(screen, "Mana {}".format(mana), (25, 250), font, 1, (0, 20, 255), 2)
    screen = cv2.putText(screen, "Spell mana {}".format(spell_mana), (25, 300), font, 1, (0, 100, 255), 2)
    # screen = cv2.putText(screen, "Prev Mana {}".format(prev_mana), (25, 350), font, 1, (0, 20, 255), 2)

    # Show current frame
    # screen_resized = cv2.resize(screen, (1280, 720))
    # cv2.imshow('LOR Bot', cv2.cvtColor(screen_resized, cv2.COLOR_BGR2RGB))

    # Show board state
    cv2.imshow('Board state', board_state_img)

    # Quit condition
    if cv2.waitKey(25) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break

    time.sleep(1)

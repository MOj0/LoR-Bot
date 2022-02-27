import numpy as np
import cv2
from PIL import ImageGrab, Image
import win32api
import win32con
import time
import keyboard
import os
import win32gui
from termcolor import colored
import urllib.request
import json
import pytesseract
import re


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


def select_deck():
    vals = [(0.04721, 0.33454), (0.15738, 0.33401), (0.33180, 0.30779), (0.83213, 0.89538)]
    for val in vals:
        v = (window_info[0] + val[0] * window_width, window_info[1] + val[1] * window_height)
        click(int(v[0]), int(v[1]))
        time.sleep(0.7)


def get_game_state() -> str:
    # Mulligan check
    for in_game_card in game_data["Rectangles"]:
        card_code = in_game_card["CardCode"]
        if card_code == "face" or card_code not in ALL_CARDS:  # TODO: Parse other sets and remove second part of condition!
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

    # Check if its our turn
    hsv = cv2.cvtColor(turn_btn_sub_img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (15, 180, 255), (20, 200, 255))  # Blue color space
    target = cv2.cvtColor(cv2.bitwise_and(turn_btn_sub_img, turn_btn_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
    cv2.imshow("BLUE turn button end check", target)
    if cv2.countNonZero(target) < 8:  # End turn button is GRAY
        return "Opponent_Turn"

    # Check if local_player has the attack token
    attack_token_bound_l_x = int(window_width * attack_token_bounds[0][0])
    attack_token_bound_l_y = int(window_height * attack_token_bounds[0][1])
    attack_token_bound_r_x = int(window_width * attack_token_bounds[1][0])
    attack_token_bound_r_y = int(window_height * attack_token_bounds[1][1])
    for img in images:
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

    return "Defend_Turn"  # TODO: Other checks?


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


# INIT
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


class InGameCard(Card):
    def __init__(self, card, x, y, w, h, is_local):
        super().__init__(card.name, card.cost, card.attack, card.health, card.type, card.keywords)
        self.top_center = (int(x + w / 2), int(y - h / 4))
        self.is_local = is_local

    def __str__(self):
        return "InGameCard({} -- top_center:({}); is_local:{})".format(super().__str__(), self.top_center, self.is_local)


font = cv2.FONT_HERSHEY_SIMPLEX
font_color = (0, 0, 255)
window_info = [-1, -1, -1, -1]  # [location, size]

turn_btn_pos = (0.86356, 0.54873)
attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
turn_btn_bounds = ((0.8, 0.45), (0.99, 0.6))
attack_token_count = []  # If 4 values are > 10, we are on the attack turn
# Menus, InProgress(Mulligan, Opponent_Turn, Defend_Turn, Attack_Turn, Attacking, Blocking, Round_End, Pass), (HOLD)
game_state = ""
mana = 1
spell_mana = 0
round = 1

# PARSING
deck_data = json.load(open("set1-en_us.json", encoding="utf8"))
print(deck_data)

# TODO: Parse other sets!
ALL_CARDS = {card["cardCode"]: Card(card["name"], card["cost"], card["attack"],
                                    card["health"], card["type"], card["keywords"]) for card in deck_data}

GAME_DATA_LINK = "http://127.0.0.1:21337/positional-rectangles"
DECK_LINK = "http://127.0.0.1:21337/static-decklist"
GAME_RESULT_LINK = "http://127.0.0.1:21337/game-result"


# MAIN
win32gui.EnumWindows(window_callback, window_info)
if window_info == [-1, -1, -1, -1]:
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)

while (True):
    # GET DATA
    win32gui.EnumWindows(window_callback, window_info)  # Updates the window_info

    game_url = urllib.request.urlopen(GAME_DATA_LINK)
    game_data = json.loads(game_url.read().decode())
    # print(game_data)

    window_x, window_y, window_width, window_height = (window_info[0], window_info[1], game_data["Screen"]
                                                       ["ScreenWidth"], game_data["Screen"]["ScreenHeight"])

    images = [ImageGrab.grab(bbox=(window_x, window_y, window_x + window_width, window_y +
                             window_height), all_screens=True) for _ in range(4)]
    image = images[-1]
    screen = np.array(image)

    # keyboard.on_release_key("ctrl", ...)
    game_state = "(HOLD)" if keyboard.is_pressed("ctrl") else game_data["GameState"]

    if game_state != "(HOLD)":
        if game_state == "Menus":
            print("SELECTING DECK NOW!")
            select_deck()
            time.sleep(4)
            continue

        # GET (game) STATE
        # game_state = get_game_state()

        # Get mana
        # NOTE: Values are hardcoded (only works fullscreen on second monitor)
        mana_label = np.array(image.crop(box=(1585, 638, 1635, 675)))
        # TODO: READ THE MANA CORRECTLY
        # cv2.imshow("mana_label", cv2.cvtColor(mana_label, cv2.COLOR_BGR2GRAY))
        # mana_amount = pytesseract.image_to_string(cv2.cvtColor(
        #     mana_label, cv2.COLOR_BGR2GRAY), config=r'--psm 10')
        # print("mana: ", mana_amount)

        mana_label = cv2.cvtColor(mana_label, cv2.COLOR_BGR2GRAY)
        # hsv = cv2.cvtColor(mana_label, cv2.COLOR_BGR2HSV)
        # h, s, v = cv2.split(hsv)
        # # use clahe to improve contrast
        # clahe = cv2.createCLAHE(clipLimit=1)
        # contrast = clahe.apply(v)
        mana_label = cv2.Canny(mana_label, 80, 110)
        cv2.imshow("canny", mana_label)

        mana_amount = pytesseract.image_to_string(mana_label, config=r'--psm 10 -c tessedit_char_whitelist=0123456789')
        print("mana: ", mana_amount)


        # gray = cv2.cvtColor(mana_label, cv2.COLOR_BGR2GRAY)
        # thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 13, 2)
        # erode = cv2.erode(thresh, np.array((15, 15)), iterations=1)
        # cv2.imshow("erode", erode)
        # text = pytesseract.image_to_string(erode, config="--psm 10")
        # text = re.sub('[^A-Za-z0-9]+', '\n', text)
        # print("mana: ", text)

        # im = mana_label
        # imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        # ret, thresh = cv2.threshold(imgray, 127, 255, 0)
        # contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # # cv2.imshow("contours", contours)
        # cv2.drawContours(mana_label, contours, -1, (0,255,0), 3)
        # cv2.imshow("mana_label", mana_label)






        # if game_state == "Opponent_Turn":
        #     time.sleep(1)
        #     continue

        #  # Get deck
        # deck_url = urllib.request.urlopen(DECK_LINK)
        # deck_data = json.loads(deck_url.read().decode())
        # deck = [ALL_CARDS[cardCode] for cardCode, num_cards in deck_data["CardsInDeck"].items()
        #         for _ in range(num_cards)]

        # # PLAY
        # # Get cards in game
        # in_game_cards = []
        # for in_game_card in game_data["Rectangles"]:
        #     card_code = in_game_card["CardCode"]
        #     if card_code == "face" or card_code not in ALL_CARDS:  # TODO: Parse other sets and remove second part of condition!
        #         continue

        #     c = ALL_CARDS[card_code]
        #     x = in_game_card["TopLeftX"]
        #     y = in_game_card["TopLeftY"]
        #     w = in_game_card["Width"]
        #     h = in_game_card["Height"]
        #     local_player = in_game_card["LocalPlayer"]
        #     in_game_card_obj = InGameCard(c, x, y, w, h, local_player)
        #     in_game_cards.append(in_game_card_obj)

        #     # Draw circle in the top center of cards
        #     circle_x = in_game_card_obj.top_center[0]
        #     circle_y = window_height - in_game_card_obj.top_center[1]
        #     screen = cv2.circle(screen, (circle_x, circle_y), 20, (255, 0, 0), 2)

        # if game_state == "Mulligan":
        #     # (Hard) Mulligan
        #     for in_game_card_obj in in_game_cards:
        #         if in_game_card_obj.get_name() != "Zed" and in_game_card_obj.get_name() != "Shark Chariot":
        #             cx = window_x + in_game_card_obj.top_center[0]
        #             cy = window_y + window_height - in_game_card_obj.top_center[1]
        #             print("not Zed or Shark Chariot, clicking at", cx, cy)
        #             click(cx, cy)
        #             time.sleep(0.5)
        #     print("Confirming mulligan")
        #     click(window_x + window_width * turn_btn_pos[0], window_y + window_height * turn_btn_pos[1])
        # elif game_state == "Round_End":
        #     spell_mana = min(spell_mana + mana, 3)
        #     round += 1
        #     mana = round
        #     keyboard.send("space")
        # elif game_state == "Pass":
        #     keyboard.send("space")
        # elif game_state == "Defend_Turn" or game_state == "Attack_Turn":
        #     playable_cards = filter(lambda card: card.is_local and card.cost <= mana, in_game_cards)
        #     if not playable_cards and game_state == "Attack_Turn":
        #         keyboard.send("a")
        #         time.sleep(0.75)
        #         keyboard.send("space")
        #     else:
        #         for playable_card_in_hand in playable_cards:
        #             print("Playing card: ", playable_card_in_hand)
        #             play_card(playable_card_in_hand)
        #             mana -= playable_card_in_hand.cost
        #             break

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

    screen = cv2.putText(screen, "Round {}".format(round), (25, 200), font, 1, (0, 255, 255), 2)
    screen = cv2.putText(screen, "Mana {}".format(mana), (25, 250), font, 1, (0, 20, 255), 2)
    screen = cv2.putText(screen, "Spell mana {}".format(spell_mana), (25, 300), font, 1, (0, 100, 255), 2)

    # Show current frame
    cv2.imshow('LOR Bot', cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))

    # Quit condition
    if cv2.waitKey(25) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break

    time.sleep(1)

# # OLD (CV)
# while (True):
#     win32gui.EnumWindows(window_callback, window_info)
#     window_width = window_info[2] - window_info[0]
#     window_height = window_info[3] - window_info[1]

#     image = ImageGrab.grab(bbox=(window_info[:4]), all_screens=True)
#     screen = np.array(image)

#     # screen = process_img(screen)

#     # Mouse position (percentage)
#     mousePosText = "{:.5f}".format((win32api.GetCursorPos()[0] - window_info[0]) / window_width) + \
#         ", " + "{:.5f}".format((win32api.GetCursorPos()[1] - window_info[1]) / window_height)
#     screen = cv2.putText(screen, mousePosText, (25, 150), font, 0.5, (0, 255, 0), 1)
#     print(mousePosText)

#     # Show current frame
#     cv2.imshow('LOR Bot', cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))

#     # Quit condition
#     if cv2.waitKey(25) & 0xFF == ord('q'):
#         cv2.destroyAllWindows()
#         break

#     time.sleep(1)


################ OLD ###################
# # monitor = win32api.EnumDisplayMonitors()
# # print(win32api.GetMonitorInfo(monitor[0][0]))

# screenRatio = 0.8
# # screenDeltaX = 384
# # screenDeltaY = 216

# # global variables
# width = win32api.GetSystemMetrics(0) // 2
# height = win32api.GetSystemMetrics(1)
# vertices = np.array([[190, 660], [250, 655], [400, 650], [550, 652], [850, 660], [850, 475], [900, 457],
#                      [850, 660], [720, 720], [670, 720], [670, 735], [720, 735], [770, 900], [400, 900], [190, 900],
#                      [190, 660], [310, 760], [330, 760], [330, 730], [310, 730]])

# for i in range(len(vertices)):
#     vertices[i][1] = vertices[i][1]-160

# coord = 0
# atk_counter = 1
# font = cv2.FONT_HERSHEY_SIMPLEX
# font_color = (255, 0, 0)
# text = ""


# def play_card(x, y):
#     y += 40
#     for offset in range(-56, 57, 56):
#         x += offset
#         hold(x, y)
#         for i in range(3):
#             time.sleep(0.5)
#             win32api.SetCursorPos((x, y - 70 * i))
#         time.sleep(0.3)
#         release(x, y - 210)
#         time.sleep(0.3)


# def attack(x, y, counter):
#     deltaX = 100
#     y += 45
#     hold(x, y)
#     for i in range(3):
#         time.sleep(0.3)
#         win32api.SetCursorPos((x, y - 40 * i))
#     time.sleep(0.5)
#     release(deltaX * counter, y - 120)
#     time.sleep(0.3)


# def click(x, y):
#     win32api.SetCursorPos((x, y))
#     win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
#     win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


# def hold(x, y):
#     win32api.SetCursorPos((x, y))
#     time.sleep(0.1)
#     win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)


# def release(x, y):
#     win32api.SetCursorPos((x, y))
#     win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


# def roi(img, vertices):
#     mask = np.zeros_like(img)
#     cv2.fillPoly(mask, vertices, (255, 255, 255))
#     masked = cv2.bitwise_and(img, mask)
#     return masked


# def process_img(img):
#     image = roi(img, [vertices])
#     hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

#     mask = cv2.inRange(hsv, (15, 180, 255), (20, 200, 255))  # check for blue pixels

#     global coord
#     coord = cv2.findNonZero(mask)

#     # #what AI sees ...
#     imask = mask > 0  # get all blue pixels
#     processed_img = np.zeros_like(image, np.uint8)
#     processed_img[imask] = img[imask]  # replace all mask pixels with original pixels
#     return processed_img
#     # #...

#     return image


# def main():
#     global atk_counter, text
#     while (True):
#         screen = np.array(ImageGrab.grab(bbox=(0, 200, width+200, height+200)))
#         screen = process_img(screen)

#         # Play
#         if np.all(coord):
#             rows = coord.shape[0]
#             cols = coord.shape[1]
#             target_x = int(coord[rows - 1, cols - 1][0] * 0.75)
#             target_y = coord[rows - 1, cols - 1][1]
#             cv2.circle(screen, (target_x, target_y), 20, (255, 0, 0), 8)
#             text = str(target_x) + ", " + str(target_y)

#             if target_x > 600:  # pass turn
#                 text = "pass turn " + str(target_x) + ", " + str(target_y)
#                 atk_counter = 1
#                 click(700, 420)
#             elif target_y < 580:  # attack
#                 text = "attack " + str(target_x) + ", " + str(target_y)
#                 keyboard.send("a")
#                 click(target_x, target_y)
#                 time.sleep(1)
#                 attack(target_x, target_y, atk_counter)
#                 atk_counter += 1
#             else:  # play card
#                 text = "play card " + str(target_x) + ", " + str(target_y)
#                 atk_counter = 1
#                 click(target_x - 20, target_y+30)
#                 click(target_x + 20, target_y+30)
#                 play_card(target_x, target_y)

#             if atk_counter > 6:
#                 atk_counter = 1

#             time.sleep(0.3)

#         # putText(image, text, (x, y), font, textScale, color, [thickness])
#         screen = cv2.putText(screen, text, (50, 50), font, 1, font_color, 2)

#         # MOUSE POSITION TESTING
#         mousePosText = str(win32api.GetCursorPos()[0]) + ", " + str(win32api.GetCursorPos()[1])
#         screen = cv2.putText(screen, mousePosText, (50, 150), font, 1, (0, 255, 0), 2)

#         # show current frame
#         cv2.imshow('window', cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))

#         click(580, 650)  # Continue
#         time.sleep(0.5)

#         # Quit condition
#         if cv2.waitKey(25) & 0xFF == ord('q'):
#             cv2.destroyAllWindows()
#             break


# for i in range(2)[::-1]:
#     print(i + 1)
#     time.sleep(1)

# main()

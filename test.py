import masks
import numpy as np
import cv2
from PIL import ImageGrab
import win32api
import time
import win32gui
from termcolor import colored
import urllib.request
import json


# FUNCTIONS

def window_callback(handle, window):
    if win32gui.GetWindowText(handle) == "Legends of Runeterra":
        rect = win32gui.GetWindowRect(handle)
        for i, r in enumerate(rect):
            window[i] = r


def yuh():
    pass
    # # Check if local_player has the attack token
    # attack_token_bound_l_x = int(window_width * attack_token_bounds[0][0])
    # attack_token_bound_l_y = int(window_height * attack_token_bounds[0][1])
    # attack_token_bound_r_x = int(window_width * attack_token_bounds[1][0])
    # attack_token_bound_r_y = int(window_height * attack_token_bounds[1][1])
    # for img in frames:
    #     attack_token_sub_img = np.array(img.crop(
    #         box=(attack_token_bound_l_x, attack_token_bound_l_y, attack_token_bound_r_x, attack_token_bound_r_y)))
    #     hsv = cv2.cvtColor(attack_token_sub_img, cv2.COLOR_BGR2HSV)
    #     mask = cv2.inRange(hsv, (100, 192, 160), (120, 255, 255))  # Orange
    #     target = cv2.cvtColor(cv2.bitwise_and(attack_token_sub_img,
    #                           attack_token_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
    #     cv2.imshow("attack token check", target)
    #     num_orange_px = cv2.countNonZero(target)
    #     if num_orange_px <= 10:  # Not enough orange pixels for attack token
    #         break
    # else:
    #     return "Attack_Turn"

    # return "Defend_Turn"



# INIT
font = cv2.FONT_HERSHEY_SIMPLEX
font_color = (0, 0, 255)
window_info = [-1, -1, -1, -1]  # [location, size]

turn_btn_pos = (0.86356, 0.54873)
attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
turn_btn_bounds = ((0.8, 0.45), (0.99, 0.6))
attack_token_count = []  # If 4 values are > 10, we are on the attack turn
# game_state OPTIONS: Menus, InProgress(Mulligan, Opponent_Turn, Defend_Turn, Attack_Turn, Attacking, Blocking, Round_End, Pass), (HOLD)
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


# MAIN
win32gui.EnumWindows(window_callback, window_info)
if window_info == [-1, -1, -1, -1]:
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)

GAME_DATA_LINK = "http://127.0.0.1:21337/positional-rectangles"

MANA_MASKS = [masks.ZERO, masks.ONE, masks.TWO, masks.THREE, masks.FOUR,
              masks.FIVE, masks.SIX, masks.SEVEN, masks.EIGHT, masks.NINE, masks.TEN]


while (True):
    # Get window data
    win32gui.EnumWindows(window_callback, window_info)  # Updates the window_info

    # Window Handle info
    window_x, window_y, window_width, window_height = window_info[0], window_info[1], window_info[2] - \
        window_info[0], window_info[3] - window_info[1]

    frames = [ImageGrab.grab(bbox=(window_x, window_y, window_x + window_width, window_y +
                             window_height), all_screens=True) for _ in range(4)]
    image = frames[-1]
    screen = np.array(image)

    # GET MANA TODO: Find the actual mana value inside mana_edges
    mana_vals = []

    # for image in frames:
    mana_number = np.array(image.crop(box=(int(window_width * 0.785), int(window_height *
                                0.58), int(window_width * 0.91), int(window_height * 0.64))))
    mana_number_gray = cv2.cvtColor(mana_number, cv2.COLOR_BGR2GRAY)
    mana_edges = cv2.Canny(mana_number_gray, 100, 100)

    # for i, mask in enumerate(MANA_MASKS):
    #     num_mask_px = sum((val for line in mask for val in line))
    #     num_match_px = sum(map(bool, (val for e, z in zip(mana_edges, mask) for val in e[z])))
    #     match_rate = num_match_px / num_mask_px
    #     if match_rate > 0.95:
    #         mana_vals.append(i)
    #         break

    # if mana_vals and mana_vals.count(mana_vals[0]) == len(mana_vals):
    #     mana_number_gray = cv2.putText(mana_number_gray, "{}".format(mana_vals[0]), (0, 20), font, 1, (255, 255, 255), 2)
    #     cv2.imshow("mana_label", mana_number_gray)

    # mana = mana_vals[0] if mana_vals else -1

    cv2.imshow('MANA', mana_edges)
    # cv2.imshow('MANA', cv2.resize(mana_number, (300, 300)))




    # # CHECK TURN BUTTON STATUS
    # turn_btn_sub_img = np.array(image.crop(box=(int(window_width * 0.77), int(window_height *
    #                             0.42), int(window_width * 0.93), int(window_height * 0.58))))
    # hsv = cv2.cvtColor(turn_btn_sub_img, cv2.COLOR_BGR2HSV)
    # mask = cv2.inRange(hsv, (5, 200, 200), (15, 255, 255))  # Blue color space
    # target = cv2.cvtColor(cv2.bitwise_and(turn_btn_sub_img, turn_btn_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
    # cv2.imshow("BLUE turn button end check", target)
    # # if cv2.countNonZero(target) < 100:  # End turn button is GRAY
    # #     pass


    # # DRAW + CV stuff
    # # Mouse position (relative to window)
    # mousePosText = str(win32api.GetCursorPos()[0]) + \
    #     ", " + str(win32api.GetCursorPos()[1])
    # screen = cv2.putText(screen, mousePosText, (25, 150), font, 1, (0, 255, 0), 2)

    # # # Mouse position (percentage)
    # # mousePosText = "{:.5f}".format((win32api.GetCursorPos()[0] - window_info[0]) / window_width) + \
    # #     ", " + "{:.5f}".format((win32api.GetCursorPos()[1] - window_info[1]) / window_height)
    # # screen = cv2.putText(screen, mousePosText, (25, 150), font, 1, (0, 255, 0), 2)

    # Show current frame
    screen_resized = cv2.resize(screen, (1280, 720))
    cv2.imshow('LOR Bot', cv2.cvtColor(screen_resized, cv2.COLOR_BGR2RGB))

    # Quit condition
    if cv2.waitKey(25) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break
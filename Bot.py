import cv2
import masks
import numpy as np
from PIL import ImageGrab
import win32api
import win32con
import keyboard
import win32gui
import json
import os
from time import sleep
from collections import defaultdict
from Card import Card, InGameCard


MANA_MASKS = (masks.ZERO, masks.ONE, masks.TWO, masks.THREE, masks.FOUR,
              masks.FIVE, masks.SIX, masks.SEVEN, masks.EIGHT, masks.NINE, masks.TEN)
NUM_PX_MASK = tuple(sum(val for line in mask for val in line) for mask in MANA_MASKS)


class Bot:
    def __init__(self, is_vs_ai=True):
        self.is_vs_ai = is_vs_ai
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_color = (0, 0, 255)
        self.window_info = [-1, -1, -1, -1]  # [location, size]
        self.window_x = 0
        self.window_y = 0
        self.window_width = 0
        self.window_height = 0
        self.game_data = {}
        self.game_result = {}
        self.cards_data = {}
        self.all_cards = {}
        self.attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
        self.turn_btn_pos = (0.86356, 0.54873)
        self.board_state = {}
        self.game_state = ""
        self.prev_game_state = ""
        self.mana = 1
        self.prev_mana = 1
        self.spell_mana = 0
        self.turn = 1
        self.games_won = 0
        self.n_games = 0
        self.first_pass_blocking = False
        self.deck_type = ""  # Ephemeral, Aggro
        self.block_counter = 0
        self.game_id = -2
        self.prev_game_id = -2


    def _update_window_info(self, handle, window_info):
        if win32gui.GetWindowText(handle) == "Legends of Runeterra":
            rect = win32gui.GetWindowRect(handle)
            for i, r in enumerate(rect):
                window_info[i] = r

    def _get_board_state(self):
        board_state = defaultdict(list)
        if not self.game_data:
            self.board_state = board_state
            return

        for in_game_card in self.game_data["Rectangles"]:
            card_code = in_game_card["CardCode"]
            if card_code == "face":
                continue

            c = self.all_cards[card_code]
            x = in_game_card["TopLeftX"]
            y = in_game_card["TopLeftY"]
            w = in_game_card["Width"]
            h = in_game_card["Height"]
            local_player = in_game_card["LocalPlayer"]
            in_game_card_obj = InGameCard(c, x, y, w, h, local_player)

            card_y = self.window_height - in_game_card_obj.top_center[1]
            ratio = card_y / self.window_height
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

        self.board_state = board_state

    def _get_game_state(self, frames, image) -> str:
        if not self.game_data or self.game_data["GameState"] == "Menus":
            return "Menus"

        # Mulligan check
        for in_game_card in self.game_data["Rectangles"]:
            card_code = in_game_card["CardCode"]
            if card_code == "face":
                continue

            c = self.all_cards[card_code]
            x = in_game_card["TopLeftX"]
            y = in_game_card["TopLeftY"]
            w = in_game_card["Width"]
            h = in_game_card["Height"]
            local_player = in_game_card["LocalPlayer"]
            in_game_card_obj = InGameCard(c, x, y, w, h, local_player)

            circle_y = self.window_height - in_game_card_obj.top_center[1]
            if not local_player or not(circle_y < self.window_height / 2):
                break
        else:
            return "Mulligan"

        if len(self.board_state["opponent_cards_attk"]):
            return "Blocking"

        # Check if its our turn
        turn_btn_sub_img = np.array(image.crop(box=(int(self.window_width * 0.77), int(self.window_height *
                                    0.42), int(self.window_width * 0.93), int(self.window_height * 0.58))))
        hsv = cv2.cvtColor(turn_btn_sub_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (5, 200, 200), (15, 255, 255))  # Blue color space
        target = cv2.cvtColor(cv2.bitwise_and(turn_btn_sub_img, turn_btn_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
        # cv2.imshow("BLUE turn button end check", target)
        if cv2.countNonZero(target) < 100:  # End turn button is GRAY
            return "Opponent_Turn"

        # Check if local_player has the attack token
        attack_token_bound_l_x = int(self.window_width * self.attack_token_bounds[0][0])
        attack_token_bound_l_y = int(self.window_height * self.attack_token_bounds[0][1])
        attack_token_bound_r_x = int(self.window_width * self.attack_token_bounds[1][0])
        attack_token_bound_r_y = int(self.window_height * self.attack_token_bounds[1][1])
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

    def _get_mana(self, frames):
        # Magic
        mana_vals = tuple(i for image in frames for i, mask in enumerate(MANA_MASKS) if sum(map(bool, (val for edge, msk in zip(cv2.Canny(cv2.cvtColor(
            np.array(image.crop(box=(1585, 638, 1635, 675))), cv2.COLOR_BGR2GRAY), 100, 100), mask) for val in edge[msk]))) / NUM_PX_MASK[i] > 0.95)

        self.mana = mana_vals[0] if mana_vals else -1

    def _get_deck_type(self):
        if self.cards_data and self.cards_data["CardsInDeck"]:
            deck = (self.all_cards[cardCode] for cardCode, num_cards in self.cards_data["CardsInDeck"].items()
                    for _ in range(num_cards))
            self.deck_type = "Ephemeral" if any("Ephemeral" in card.keywords for card in deck) else "Aggro"

    def click(self, pos, y=None):
        if y is not None:
            x = pos
        else:
            (x, y) = pos

        (x, y) = (int(x), int(y))

        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def hold(self, pos, y=None):
        if y is not None:
            x = pos
        else:
            (x, y) = pos
        win32api.SetCursorPos((x, y))
        sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)

    def release(self, pos, y=None):
        if y is not None:
            x = pos
        else:
            (x, y) = pos
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def start(self):
        # Get window data
        win32gui.EnumWindows(self._update_window_info, self.window_info)
        self.window_x, self.window_y, self.window_width, self.window_height = self.window_info[0], self.window_info[
            1], self.window_info[2] - self.window_info[0], self.window_info[3] - self.window_info[1]

        # Cards parsing
        (_, _, card_set_files) = next(os.walk("card_sets"))
        cards_data = []
        for card_set in card_set_files:
            cards_data += json.load(open("card_sets/"+card_set, encoding="utf8"))

        self.all_cards = {card["cardCode"]: Card(card["name"], card["cost"], card["attack"],
                                                 card["health"], card["type"], card["keywords"]) for card in cards_data}

        self.run()

    def run(self):
        while True:
            if self.game_result:
                self.game_id = int(self.game_result["GameID"])
                if self.game_id > self.prev_game_id:  # Game is finished
                    self.games_won += 1 * self.game_result["LocalPlayerWon"]
                    self.n_games += 1
                    self.prev_game_id = self.game_id

                    print("Game ended... waiting for animations")
                    sleep(20)
                    self.continue_and_replay()
                    continue

            # Get window data
            win32gui.EnumWindows(self._update_window_info, self.window_info)
            self.window_x, self.window_y, self.window_width, self.window_height = self.window_info[0], self.window_info[
                1], self.window_info[2] - self.window_info[0], self.window_info[3] - self.window_info[1]

            # 4 frames are needed becuase of mana recognition!
            frames = [ImageGrab.grab(bbox=(self.window_x, self.window_y, self.window_x + self.window_width, self.window_y +
                                        self.window_height), all_screens=True) for _ in range(4)]
            image = frames[-1]
            # screen = np.array(image)

            self.prev_game_state = self.game_state

            self._get_board_state()
            self.game_state = "(HOLD)" if keyboard.is_pressed("ctrl") else self._get_game_state(frames, image)
            self._get_mana(frames)
            self._get_deck_type()

            if not self.is_state_ok():
                continue
            self.play()

    def continue_and_replay(self):
        sleep(4)
        continue_btn_pos = (self.window_x + 0.66 * self.window_width, self.window_y + self.window_height * 0.90)
        for _ in range(4):
            self.click(continue_btn_pos)
            sleep(1.5)
        sleep(1)


    def is_state_ok(self) -> bool:
        if self.game_state == "(HOLD)":
            return False
        if self.game_state == "Menus":
            print("SELECTING DECK NOW!")
            self.select_deck()
            sleep(5)
            self.prev_game_state = self.game_state
            return False
        if self.game_state == "Mulligan" and self.prev_game_state == "Menus":  # Double-check so we don't get False Positives!
            print("Thinking for mulligan...")
            sleep(10)
            self.prev_game_state = self.game_state
            return False
        if self.mana == -1:
            print("Unknown mana...")
            sleep(1.5)
            return False
        if self.mana > self.turn:  # New turn
            self.spell_mana = min(self.spell_mana + self.prev_mana, 3)
            self.turn = self.mana
            self.prev_mana = self.mana
            self.first_pass_blocking = False
            self.block_counter = 0
            sleep(2)
            return False
        return True

    def play(self):
        in_game_cards = [card for cards in self.board_state.values() for card in cards]

        if self.game_state == "Mulligan":
            # Reset variables
            self.mana = self.prev_mana = self.turn = 1
            self.spell_mana = 0
            self.block_counter = 0

            # Mulligan
            for in_game_card_obj in in_game_cards:
                if in_game_card_obj.cost > 3:
                    cx = self.window_x + in_game_card_obj.top_center[0]
                    cy = self.window_y + self.window_height - in_game_card_obj.top_center[1]
                    print("Cost greater than 3, clicking at", cx, cy)
                    self.click(cx, cy)
                    sleep(0.5)
            print("Confirming mulligan")
            self.click(self.window_x + self.window_width *
                       self.turn_btn_pos[0], self.window_y + self.window_height * self.turn_btn_pos[1])
        elif self.game_state == "Opponent_Turn":
            sleep(3)
            return
        elif self.game_state == "Blocking":
            if not self.first_pass_blocking:
                self.first_pass_blocking = True
                print("first blocking pass...")
                sleep(5)
                return

            for i, blocking_card in enumerate(self.board_state["cards_board"]):
                if i < self.block_counter or blocking_card.get_name() == "Zed" or "Can't Block" in blocking_card.keywords:
                    continue
                if self.blocked_with(blocking_card, self.board_state["opponent_cards_attk"], self.board_state["cards_attk"]):
                    self.block_counter = (self.block_counter + 1) % len(self.board_state["cards_board"])
                    break
            else:
                self.block_counter = 0
                keyboard.send("space")
        elif self.game_state == "Defend_Turn" or self.game_state == "Attack_Turn":
            if len(self.board_state["spell_stack"]) != 0 and all(card.is_spell() for card in self.board_state["spell_stack"]):
                keyboard.send("space")
                sleep(1)
            playable_cards = sorted(filter(lambda card: card.get_name() != "Shadowshift" and card.cost <= self.mana or card.is_spell()
                                           and card.cost <= self.mana + self.spell_mana, self.board_state["cards_hand"]), key=lambda card: card.cost, reverse=True)
            if len(playable_cards) == 0 and self.game_state == "Attack_Turn" or len(self.board_state["cards_board"]) == 6:
                keyboard.send("a")
                sleep(1.25)
                keyboard.send("space")
            else:
                for playable_card_in_hand in playable_cards:
                    if self.deck_type == "Ephemeral" and (self.game_state == "Attack_Turn" and ("Ephemeral" in playable_card_in_hand.keywords or playable_card_in_hand.get_name() in ("Zed", "Hecarim", "Commander Ledros") or playable_card_in_hand.is_spell())
                                                          or self.game_state == "Defend_Turn" and "Ephemeral" not in playable_card_in_hand.keywords and not playable_card_in_hand.is_spell()) \
                            or self.deck_type == "Aggro":
                        print("Playing card: ", playable_card_in_hand)
                        self.play_card(playable_card_in_hand)
                        diff = playable_card_in_hand.cost
                        if playable_card_in_hand.is_spell():
                            diff = max(0, playable_card_in_hand.cost - self.spell_mana)
                            self.spell_mana = max(0, self.spell_mana - playable_card_in_hand.cost)
                        self.mana -= diff
                        self.prev_mana = self.mana
                        break
                else:
                    if self.game_state == "Attack_Turn":
                        keyboard.send("a")
                        sleep(1.25)
                    keyboard.send("space")
                    sleep(2)

    def blocked_with(self, blocking_card, enemy_cards, ally_cards):
        for enemy_card in enemy_cards:
            if "Elusive" in enemy_card.keywords:
                continue
            is_blockable = True
            # if "Ephemeral" in blocking_card.keywords or enemy_card.attack < blocking_card.health:  # Defensive block
            if "Ephemeral" in blocking_card.keywords or enemy_card.health <= blocking_card.attack:  # Aggressive block
                for ally_card in ally_cards:  # Check if card is already blocked or elusive
                    if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                        is_blockable = False
                        break
                if is_blockable:
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                    return True
        return False

    def drag_card_from_to(self, pos_src, pos_dest):
        pos_src = (self.window_x + pos_src[0], self.window_y + self.window_height - pos_src[1])
        pos_dest = (self.window_x + pos_dest[0], self.window_y + self.window_height - pos_dest[1])
        self.hold(pos_src)
        sleep(0.3)
        win32api.SetCursorPos(((pos_src[0] + pos_dest[0]) // 2, (pos_src[1] + pos_dest[1]) // 2))
        sleep(1)
        self.release(pos_dest)
        sleep(0.5)

    def play_card(self, card):
        (x, y) = (self.window_x + card.top_center[0], self.window_y + self.window_height - card.top_center[1])
        print("Playing at: ", x, y)
        self.hold(x, y)
        for i in range(3):
            sleep(0.5)
            win32api.SetCursorPos((x, int(y - self.window_height / 7 * i)))
        sleep(0.3)
        self.release(x, int(y - 3 * self.window_height / 7))
        sleep(0.3)
        if card.is_spell():
            sleep(1)
            keyboard.send("space")

    def select_deck(self):
        vals_ai = [(0.04721, 0.33454), (0.15738, 0.33401), (0.33180, 0.30779), (0.83213, 0.89538)]
        vals_pvp = [(0.04721, 0.33454), (0.15738, 0.25), (0.33180, 0.30779), (0.83213, 0.89538)]
        vals = vals_ai if self.is_vs_ai else vals_pvp
        for val in vals:
            v = (self.window_info[0] + val[0] * self.window_width, self.window_info[1] + val[1] * self.window_height)
            self.click(int(v[0]), int(v[1]))
            sleep(0.7)

    def display_board_state(self):
        shape = (720, 1280)
        background_color = (0.0, 0.4, 0.1) if self.game_state == "(HOLD)" else (0.0, 0.0, 0.0)
        board_state_img = np.full((*shape, len(background_color)), background_color)
        board_state_img = cv2.putText(board_state_img, self.deck_type, (500, 100), self.font, 1, (255, 255, 255), 2)
        board_state_img = cv2.putText(board_state_img, "{}".format(self.game_state),
                                      (1000, 40), self.font, 1, (0, 255, 255), 2)
        board_state_img = cv2.putText(board_state_img, "Round {}".format(self.turn),
                                      (1000, 80), self.font, 1, (0, 255, 255), 2)
        board_state_img = cv2.putText(board_state_img, "Mana {}".format(self.mana),
                                      (1000, 120), self.font, 1, (0, 20, 255), 2)
        board_state_img = cv2.putText(board_state_img, "Spell mana {}".format(self.spell_mana),
                                      (1000, 160), self.font, 1, (0, 100, 255), 2)
        board_state_img = cv2.putText(board_state_img, "Prev mana {}".format(self.prev_mana),
                                      (1000, 200), self.font, 1, (0, 100, 255), 2)
        board_state_img = cv2.putText(board_state_img, "Win% {}/{} ({})".format(
            self.games_won, self.n_games, ("/" if self.n_games == 0 else str(self.games_won / self.n_games)) + " %"),
            (1000, 240), self.font, 1, (0, 255, 255), 2)

        for i, (position, cards) in enumerate(self.board_state.items()):
            board_state_img = cv2.putText(board_state_img, position, (20, 30 + 150 * i), self.font, 1, (0, 255, 0), 2)
            for j, card in enumerate(cards):
                board_state_img = cv2.putText(board_state_img, card.get_name(
                ), (20, 50 + 150 * i + 25 * j), self.font, 1, (255, 0, 0), 2)

        # Show board state
        cv2.imshow('Board state', board_state_img)

    def get_display_data(self) -> dict:
        return {"game_state": self.game_state, "board_state": self.board_state, "deck_type": self.deck_type, "mana": self.mana,
                "spell_mana": self.spell_mana, "prev_mana": self.prev_mana, "games_won": self.games_won,
                "n_games": self.n_games, "turn": self.turn}

    def get_window_info(self) -> list:
        # return self.window_info
        return [self.window_x, self.window_y, self.window_width, self.window_height]

    def set_game_data(self, game_data):
        self.game_data = game_data

    def set_cards_data(self, cards_data):
        self.cards_data = cards_data
    
    def set_game_result(self, game_result):
        if not game_result:
            return
        self.game_result = game_result
        if self.game_id == -2 and self.prev_game_id == -2:
            self.game_id = int(game_result["GameID"])
            self.prev_game_id = self.game_id

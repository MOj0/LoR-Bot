from Card import InGameCard
from collections import defaultdict
import win32gui
import keyboard
from PIL import ImageGrab
import numpy as np
import constants
import cv2
from enum import Enum


class GameState(Enum):
    Hold = -1
    Menus = 0
    Mulligan = 1
    Opponent_Turn = 2
    Defend_Turn = 3
    Attack_Turn = 4
    Attacking = 5
    Blocking = 6
    Round_End = 7
    Pass = 8
    End = 9


class DeckType(Enum):
    Ephemeral = 0
    Aggro = 1


class StateMachine:
    """Determines the game state and cards on board by using the LoR API and cv2 functionality"""

    def __init__(self):
        self.game_state = GameState.Menus
        self.cards_on_board = {}
        self.deck_type = DeckType
        self.window_info = [-1, -1, -1, -1]  # [location, size]
        self.window_x = 0
        self.window_y = 0
        self.window_width = 0
        self.window_height = 0
        self.game_data = {}
        self.game_result = {}
        self.cards_data = {}
        self.frames = None
        self.games_won = 0
        self.n_games = 0
        self.first_pass_blocking = False
        self.game_id = -2
        self.prev_game_id = -2
        self.attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
        self.turn_btn_pos = (0.86356, 0.54873)

    def _update_window_info(self, handle, window_info):
        if win32gui.GetWindowText(handle) == "Legends of Runeterra":
            rect = win32gui.GetWindowRect(handle)
            for i, r in enumerate(rect):
                window_info[i] = r

    def get_game_info(self) -> tuple:
        # Get window data
        win32gui.EnumWindows(self._update_window_info, self.window_info)
        self.window_x, self.window_y, self.window_width, self.window_height = self.window_info[0], self.window_info[
            1], self.window_info[2] - self.window_info[0], self.window_info[3] - self.window_info[1]

        # 4 frames are needed becuase of mana recognition -> Moved to Bot.py
        self.frames = [ImageGrab.grab(bbox=(self.window_x, self.window_y, self.window_x + self.window_width, self.window_y +
                                            self.window_height), all_screens=True) for _ in range(4)]
        image = self.frames[-1]

        self._get_cards_on_board()
        self.game_state = self._get_game_state(self.frames, image)

        return tuple((self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won))

    def get_window_info_frames(self) -> tuple:
        return tuple((self.get_window_info(), self.frames))

    # API Stuff

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

    def _get_cards_on_board(self):
        cards_on_board = defaultdict(list)
        if not self.game_data:  # API hasn't started yet
            self.cards_on_board = cards_on_board
            return

        for in_game_card in self.game_data["Rectangles"]:
            card_code = in_game_card["CardCode"]
            if card_code == "face":
                continue

            c = constants.ALL_CARDS[card_code]
            x = in_game_card["TopLeftX"]
            y = in_game_card["TopLeftY"]
            w = in_game_card["Width"]
            h = in_game_card["Height"]
            local_player = in_game_card["LocalPlayer"]
            in_game_card_obj = InGameCard(c, x, y, w, h, local_player)

            card_y = self.window_height - in_game_card_obj.top_center[1]
            y_ratio = card_y / self.window_height
            if y_ratio > 0.97:
                cards_on_board["cards_hand"].append(in_game_card_obj)
            elif y_ratio > 0.75:
                cards_on_board["cards_board"].append(in_game_card_obj)
            elif y_ratio > 0.6:
                cards_on_board["cards_attk"].append(in_game_card_obj)
            elif y_ratio > 0.45:
                cards_on_board["spell_stack"].append(in_game_card_obj)
            elif y_ratio > 0.275:
                cards_on_board["opponent_cards_attk"].append(in_game_card_obj)
            elif y_ratio > 0.1:
                cards_on_board["opponent_cards_board"].append(in_game_card_obj)
            else:
                cards_on_board["opponent_cards_hand"].append(in_game_card_obj)

        self.cards_on_board = cards_on_board

    def _get_game_state(self, frames, image) -> str:
        if keyboard.is_pressed("ctrl"):
            return GameState.Hold

        if self.game_result:
            self._get_deck_type()
            self.game_id = int(self.game_result["GameID"])
            if self.game_id > self.prev_game_id:  # Game is finished
                self.games_won += 1 * self.game_result["LocalPlayerWon"]
                self.n_games += 1
                self.prev_game_id = self.game_id
                self.first_pass_blocking = False
                return GameState.End

        if not self.game_data or self.game_data["GameState"] == "Menus":
            return GameState.Menus

        # Mulligan check
        local_cards = filter(lambda card: card["CardCode"] !=
                             "face" and card["LocalPlayer"], self.game_data["Rectangles"])
        for in_game_card in local_cards:
            y = in_game_card["TopLeftY"]
            if y != 730:  # Mulligan y location TODO: Generalize
                break
        else:
            return GameState.Mulligan

        if len(self.cards_on_board["opponent_cards_attk"]):
            return GameState.Blocking

        # Check if its our turn
        turn_btn_sub_img = np.array(image.crop(box=(int(self.window_width * 0.77), int(self.window_height *
                                    0.42), int(self.window_width * 0.93), int(self.window_height * 0.58))))
        hsv = cv2.cvtColor(turn_btn_sub_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (5, 200, 200), (15, 255, 255))  # Blue color space
        target = cv2.cvtColor(cv2.bitwise_and(turn_btn_sub_img, turn_btn_sub_img, mask=mask), cv2.COLOR_BGR2GRAY)
        if cv2.countNonZero(target) < 100:  # End turn button is GRAY
            return GameState.Opponent_Turn

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
            return GameState.Attack_Turn

        return GameState.Defend_Turn

    def _get_deck_type(self):
        if self.cards_data and self.cards_data["CardsInDeck"]:
            deck = (constants.ALL_CARDS[cardCode] for cardCode, num_cards in self.cards_data["CardsInDeck"].items()
                    for _ in range(num_cards))
            self.deck_type = DeckType.Ephemeral if any(
                "Ephemeral" in card.keywords for card in deck) else DeckType.Aggro

    def get_display_data(self) -> dict:
        return {"game_state": self.game_state, "board_state": self.cards_on_board, "deck_type": self.deck_type,
                "games_won": self.games_won, "n_games": self.n_games}

    def get_window_info(self) -> tuple:
        # return self.window_info
        return tuple((self.window_x, self.window_y, self.window_width, self.window_height))

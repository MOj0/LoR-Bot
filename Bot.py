import cv2
import constants
import numpy as np
import win32api
import win32con
import keyboard
from time import sleep
from StateMachine import GameState, DeckType


MANA_MASKS = (constants.ZERO, constants.ONE, constants.TWO, constants.THREE, constants.FOUR,
              constants.FIVE, constants.SIX, constants.SEVEN, constants.EIGHT, constants.NINE, constants.TEN)
NUM_PX_MASK = tuple(sum(val for line in mask for val in line) for mask in MANA_MASKS)


class Bot:
    """Plays the game, responisble for logic/strategy"""

    def __init__(self, state_machine, is_vs_ai=True):
        self.state_machine = state_machine
        self.is_vs_ai = is_vs_ai
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.window_x = -1
        self.window_y = -1
        self.window_width = 0
        self.window_height = 0
        self.attack_token_bounds = ((0.78, 0.6), (0.935, 0.8))
        self.turn_btn_pos = (0.86356, 0.54873)
        self.game_result = {}
        self.cards_on_board = {}
        self.game_state = GameState
        self.deck_type = DeckType
        self.mana = 1
        self.prev_mana = 1
        self.spell_mana = 0
        self.turn = 1
        self.games_won = 0
        self.n_games = 0
        self.first_pass_blocking = False
        self.block_counter = 0

    def _get_mana(self, frames):
        # Magic
        mana_vals = tuple(i for image in frames for i, mask in enumerate(MANA_MASKS) if sum(map(bool, (val for edge, msk in zip(cv2.Canny(cv2.cvtColor(
            np.array(image.crop(box=(1585, 638, 1635, 675))), cv2.COLOR_BGR2GRAY), 100, 100), mask) for val in edge[msk]))) / NUM_PX_MASK[i] > 0.95)

        self.mana = mana_vals[0] if mana_vals else -1

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

    def run(self):
        while True:
            self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info()
            if self.game_state == GameState.End:
                print("Game ended... waiting for animations")
                sleep(20)

                # Reset variables
                self.mana = self.prev_mana = self.turn = 1
                self.spell_mana = self.block_counter = 0

                self.continue_and_replay()
                continue

            # Get window info; frames (for mana recognition), Deck Type
            window_info, frames = self.state_machine.get_window_info_frames()
            self.window_x = window_info[0]
            self.window_y = window_info[1]
            self.window_width = window_info[2]
            self.window_height = window_info[3]

            self._get_mana(frames)

            if not self.is_state_playable():
                continue
            self.play()

    def continue_and_replay(self):
        sleep(4)
        continue_btn_pos = (self.window_x + 0.66 * self.window_width, self.window_y + self.window_height * 0.90)
        for _ in range(4):
            self.click(continue_btn_pos)
            sleep(1.5)
        sleep(1)

    def is_state_playable(self) -> bool:
        if self.game_state == GameState.Hold:
            return False
        if self.game_state == GameState.Menus:
            print("SELECTING DECK NOW!")
            self.select_deck()
            sleep(5)
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
        in_game_cards = [card for cards in self.cards_on_board.values() for card in cards]

        if self.game_state == GameState.Mulligan:
            print("Thinking about mulligan...")
            sleep(10)

            # Get cards_on_board again, since they might have updated
            self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info()
            in_game_cards = [card for cards in self.cards_on_board.values() for card in cards]
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
            sleep(5)
        elif self.game_state == GameState.Opponent_Turn:
            sleep(3)
            return
        elif self.game_state == GameState.Blocking:
            if not self.first_pass_blocking:
                self.first_pass_blocking = True
                print("first blocking pass...")
                sleep(5)
                return

            for i, blocking_card in enumerate(self.cards_on_board["cards_board"]):
                if i < self.block_counter or blocking_card.get_name() == "Zed" or "Can't Block" in blocking_card.keywords:
                    continue
                if self.blocked_with(blocking_card, self.cards_on_board["opponent_cards_attk"], self.cards_on_board["cards_attk"]):
                    self.block_counter = (self.block_counter + 1) % len(self.cards_on_board["cards_board"])
                    break
            else:
                self.block_counter = 0
                keyboard.send("space")
        elif self.game_state == GameState.Defend_Turn or self.game_state == GameState.Attack_Turn:
            if len(self.cards_on_board["spell_stack"]) != 0 and all(card.is_spell() for card in self.cards_on_board["spell_stack"]):
                keyboard.send("space")
                sleep(1)
            playable_cards = sorted(filter(lambda card: card.get_name() != "Shadowshift" and (card.cost <= self.mana or card.is_spell())
                                           and card.cost <= self.mana + self.spell_mana, self.cards_on_board["cards_hand"]), key=lambda card: card.cost, reverse=True)
            if len(playable_cards) == 0 and self.game_state == GameState.Attack_Turn or len(self.cards_on_board["cards_board"]) == 6:
                keyboard.send("a")
                sleep(1.25)
                keyboard.send("space")
            else:
                for playable_card_in_hand in playable_cards:
                    if self.deck_type == DeckType.Ephemeral and (self.game_state == GameState.Attack_Turn and ("Ephemeral" in playable_card_in_hand.keywords or playable_card_in_hand.get_name() in ("Zed", "Hecarim", "Commander Ledros") or playable_card_in_hand.is_spell())
                                                                 or self.game_state == GameState.Defend_Turn and "Ephemeral" not in playable_card_in_hand.keywords and not playable_card_in_hand.is_spell()) \
                            or self.deck_type == DeckType.Aggro:
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
                    if self.game_state == GameState.Attack_Turn:
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
        self.click(x, y)
        sleep(0.5) # Wait for the card maximize animation
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
            v = (self.window_x + val[0] * self.window_width, self.window_y + val[1] * self.window_height)
            self.click(int(v[0]), int(v[1]))
            sleep(0.7)

    def get_display_data(self) -> dict:
        return {"game_state": self.game_state, "cards_on_board": self.cards_on_board, "deck_type": self.deck_type, "mana": self.mana,
                "spell_mana": self.spell_mana, "prev_mana": self.prev_mana, "games_won": self.games_won,
                "n_games": self.n_games, "turn": self.turn}

    def get_window_info(self) -> tuple:
        # return self.window_info
        return tuple((self.window_x, self.window_y, self.window_width, self.window_height))

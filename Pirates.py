from time import sleep
import keyboard
import win32api
import win32con
from constants import GameState


class Pirates:
    def __init__(self):
        self.window_x = 0
        self.window_y = 0
        self.window_height = 0
        self.block_counter = 0
        self.mulligan_cards = ("Crackshot Corsair", "Legion Rearguard",
                               "Legion Saboteur", "Precious Pet", "Prowling Cutthroat")
        self.deck = None

    def set_deck(self, deck):
        self.deck = deck

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

    def drag_card_from_to(self, pos_src, pos_dest):
        pos_src = (self.window_x + pos_src[0], self.window_y + self.window_height - pos_src[1])
        pos_dest = (self.window_x + pos_dest[0], self.window_y + self.window_height - pos_dest[1])
        self.hold(pos_src)
        sleep(0.3)
        win32api.SetCursorPos(((pos_src[0] + pos_dest[0]) // 2, (pos_src[1] + pos_dest[1]) // 2))
        sleep(1)
        self.release(pos_dest)
        sleep(0.5)

    def mulligan(self, cards, window_x, window_y, window_height):
        # Window stuff
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        for in_game_card_obj in cards:
            if in_game_card_obj.get_name() not in self.mulligan_cards:
                cx = window_x + in_game_card_obj.top_center[0]
                cy = window_y + window_height - in_game_card_obj.top_center[1]
                self.click(cx, cy)
                sleep(0.5)

    def play_card(self, card):
        (x, y) = (self.window_x + card.top_center[0], self.window_y + self.window_height - card.top_center[1])
        self.click(x, y)
        sleep(0.5)  # Wait for the card maximize animation
        self.hold(x, y)
        for i in range(3):
            sleep(0.5)
            win32api.SetCursorPos((x, int(y - self.window_height / 7 * i)))
        sleep(0.3)
        self.release(x, int(y - 3 * self.window_height / 7))
        sleep(0.3)

    def block(self, cards_on_board, window_x, window_y, window_height):
        # Window stuff
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        if any(card_on_board.get_name() == "Powder Keg" for card_on_board in (cards_on_board["cards_board"] + cards_on_board["cards_attk"])):
            for card_in_hand in cards_on_board["cards_hand"]:
                if card_in_hand.get_name() == "Make it Rain":
                    self.play_card(card_in_hand)
                    break

        for i, blocking_card in enumerate(cards_on_board["cards_board"]):
            if i < self.block_counter or "Can't Block" in blocking_card.keywords or "Immobile" in blocking_card.keywords or blocking_card.get_name() == "Crackshot Corsair":
                continue
            if self.blocked_with(blocking_card, cards_on_board["opponent_cards_attk"], cards_on_board["cards_attk"]):
                self.block_counter = (self.block_counter + 1) % len(cards_on_board["cards_board"])
                return True

        self.block_counter = 0
        return False

    def blocked_with(self, blocking_card, enemy_cards, ally_cards):
        for enemy_card in enemy_cards:
            if "Elusive" in enemy_card.keywords:
                continue
            is_blockable = True
            # if enemy_card.health <= blocking_card.attack:  # Aggressive block
            if enemy_card.attack < blocking_card.health:  # Defensive block
                for ally_card in ally_cards:  # Check if card is already blocked or elusive
                    if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                        is_blockable = False
                        break
                if is_blockable:
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                    return True
        return False

    def playable_card(self, playable_cards, game_state, cards_on_board):
        attack_sort = sorted(playable_cards, key=lambda playable_card: playable_card.cost, reverse=True)
        n_cards_on_board = len(cards_on_board["cards_board"])
        for playable_card_in_hand in attack_sort:
            name = playable_card_in_hand.get_name()
            n_summon = 2 if "summon a" in playable_card_in_hand.description_raw.lower() else 1
            all_1hp_or_lower = len(cards_on_board["cards_board"]) != 0 and  all(unit.health <= 1 for unit in cards_on_board["cards_board"])
            if name == "Imperial Demolist" and all_1hp_or_lower \
                or n_cards_on_board + n_summon > 6 \
                    or all(card.get_name() != name for card in self.deck) \
            or name == "Parrley" or name == "Make it Rain" and len(cards_on_board["opponent_cards_board"]) < 2:
                continue
            if game_state == GameState.Attack_Turn or game_state == GameState.Defend_Turn:
                return playable_card_in_hand
        return None

    def attack(self, cards_on_board, window_x, window_y, window_height):
        # Window stuff
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        for attack_card in cards_on_board["cards_attk"]:
            # Remove Crackshot Corsair from board if necessary
            if attack_card.get_name() == "Crackshot Corsair" and len(cards_on_board["opponent_cards_board"]) != 0:
                self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], window_height - 100))
                return False

        return True

    def get_card_in_hand(self, units_in_hand, select_ephemeral):
        if select_ephemeral:
            ephemerals = filter(lambda card_in_hand: "Ephemeral" in card_in_hand.keywords, units_in_hand)
            return next(ephemerals, units_in_hand[0])
        # select_ephemeral == False -> select the strongest
        return max(units_in_hand, key=lambda card_in_hand: card_in_hand.attack + card_in_hand.health)

from time import sleep
import keyboard
import win32api
import win32con
from constants import GameState


class Ephemeral:
    def __init__(self):
        self.graveyard = []
        self.block_counter = 0

    def print(self):
        print("Ephemeral")

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

    def drag_card_from_to(self, pos_src, pos_dest, window_x, window_y, window_height):
        pos_src = (window_x + pos_src[0], window_y + window_height - pos_src[1])
        pos_dest = (window_x + pos_dest[0], window_y + window_height - pos_dest[1])
        self.hold(pos_src)
        sleep(0.3)
        win32api.SetCursorPos(((pos_src[0] + pos_dest[0]) // 2, (pos_src[1] + pos_dest[1]) // 2))
        sleep(1)
        self.release(pos_dest)
        sleep(0.5)

    def mulligan(self, cards, window_x, window_y, window_height):
        for in_game_card_obj in cards:
            if in_game_card_obj.cost > 3:
                cx = window_x + in_game_card_obj.top_center[0]
                cy = window_y + window_height - in_game_card_obj.top_center[1]
                print("Cost greater than 3, clicking at", cx, cy)
                self.click(cx, cy)
                sleep(0.5)

    def block(self, cards_on_board, window_x, window_y, window_height):
        for i, blocking_card in enumerate(cards_on_board["cards_board"]):
            if i < self.block_counter or blocking_card.get_name() == "Zed" or "Can't Block" in blocking_card.keywords:
                continue
            if self.blocked_with(blocking_card, cards_on_board["opponent_cards_attk"], cards_on_board["cards_attk"], window_x, window_y, window_height):
                self.block_counter = (self.block_counter + 1) % len(cards_on_board["cards_board"])
                break
        else:
            self.block_counter = 0
            keyboard.send("space")

    def blocked_with(self, blocking_card, enemy_cards, ally_cards, window_x, window_y, window_height):
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
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos(),
                                           window_x, window_y, window_height)
                    return True
        return False

    def playable_card(self, playable_cards, game_state):
        for playable_card_in_hand in playable_cards:
            if playable_card_in_hand.get_name() == "Shadowshift":
                continue
            if game_state == GameState.Attack_Turn and ("Ephemeral" in playable_card_in_hand.keywords or playable_card_in_hand.get_name() in ("Zed", "Hecarim", "Commander Ledros") or playable_card_in_hand.is_spell()) or \
                    game_state == GameState.Defend_Turn and ("Ephemeral" not in playable_card_in_hand.keywords and not playable_card_in_hand.is_spell()):
                return playable_card_in_hand
        return None

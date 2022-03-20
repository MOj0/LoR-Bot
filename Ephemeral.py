from time import sleep
import win32api
import win32con
from constants import GameState
from collections import defaultdict


class Ephemeral:
    def __init__(self):
        self.graveyard = defaultdict(int)  # Counter of dead cards, (Harrowing) 
        self.spawn_on_attack = 0  # Increments when Shark Chariot dies
        self.block_counter = 0
        self.mulligan_cards = ("Zed", "Shark Chariot", "Shadow Fiend")
        self.hecarim_backed = False

        self.window_x = 0
        self.window_y = 0
        self.window_height = 0

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

    def block(self, cards_on_board, window_x, window_y, window_height):
        # Window stuff
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        for i, blocking_card in enumerate(cards_on_board["cards_board"]):
            if i < self.block_counter or blocking_card.get_name() == "Zed" or "Can't Block" in blocking_card.keywords:
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
            # if "Ephemeral" in blocking_card.keywords or enemy_card.attack < blocking_card.health:  # Defensive block
            if "Ephemeral" in blocking_card.keywords or blocking_card.health == 1 or enemy_card.health <= blocking_card.attack:  # Aggressive block
                for ally_card in ally_cards:  # Check if card is already blocked or elusive
                    if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                        is_blockable = False
                        break
                if is_blockable:
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                    return True
        return False

    def playable_card(self, playable_cards, game_state):
        attack_sort = sorted(playable_cards, key=lambda attack_card: attack_card.cost + 3 * int(attack_card.is_spell()) +
                             3 * int("Ephemeral" in attack_card.keywords), reverse=True)
        for playable_card_in_hand in attack_sort:
            name = playable_card_in_hand.get_name()
            if name == "Shadowshift":
                continue
            if game_state == GameState.Attack_Turn or game_state == GameState.Defend_Turn and ("Ephemeral" not in playable_card_in_hand.keywords and not playable_card_in_hand.is_spell()):
                if not playable_card_in_hand.is_spell():
                    # Assume a unit is dead as soon as you play it (its an Ephemeral deck anyways)
                    self.graveyard[playable_card_in_hand.get_name()] += 1
                return playable_card_in_hand
        return None

    def attack(self, cards_on_board, window_x, window_y, window_height):
        # Window stuff
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        n_attackers = len(cards_on_board["cards_attk"])
        n_non_ephemeral = sum(1 for attack_card in cards_on_board["cards_attk"] if "Ephemeral" not in attack_card.keywords and attack_card.get_name(
        ) != "Zed" and attack_card.get_name() != "Hecarim")
        n_to_be_spawned = self.spawn_on_attack
        for attack_card in cards_on_board["cards_attk"]:
            name = attack_card.get_name()
            if name == "Zed":
                n_to_be_spawned += 1
            elif name == "Hecarim":
                n_to_be_spawned += 2
        print("to be spawned: ", n_to_be_spawned)

        # Check if non-ephemeral unit is in danger
        for attack_card in cards_on_board["cards_attk"]:
            unit_in_danger = attack_card.attack == 0 or "Ephemeral" not in attack_card.keywords and any(map(
                lambda enemy_card: enemy_card.attack >= attack_card.health + 2, cards_on_board["opponent_cards_board"]))
            if unit_in_danger and attack_card.get_name() != "Zed" and "Elusive" not in attack_card.keywords:
                self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], window_height - 100))
                return False

        # If attack would overflow
        if n_attackers + n_to_be_spawned > 6 and n_non_ephemeral > 0:
            for attack_card in cards_on_board["cards_attk"]:
                if "Ephemeral" not in attack_card.keywords and attack_card.get_name() != "Zed" and attack_card.get_name() != "Hecarim":
                    self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], window_height - 100))
                    return False

        # Position Hecarim to the right for max damage output
        if any(map(lambda attk_card: attk_card.get_name() == "Hecarim", cards_on_board["cards_attk"])) and not self.hecarim_backed :  # Retreat Hecarim from attack if it is on board
            for attack_card in cards_on_board["cards_attk"]:
                if attack_card.get_name() == "Hecarim":
                    self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], window_height - 100))
                    self.hecarim_backed = True
                    sleep(1)
                    return False  # Not done yet
        elif self.hecarim_backed:  # Put Hecarim back in attack to the last position
            for unit_card in cards_on_board["cards_board"]:
                if unit_card.get_name() == "Hecarim":
                    self.drag_card_from_to(unit_card.get_pos(), (unit_card.get_pos()[0], window_height // 2))
                    self.hecarim_backed = False
                    sleep(1)
                    break

        n_shark_chariots = sum(
            1 for attack_card in cards_on_board["cards_attk"] if attack_card.get_name() == "Shark Chariot")
        self.spawn_on_attack = max(self.spawn_on_attack, n_shark_chariots)
        print("spawn on attack: ", self.spawn_on_attack)
        return True

    def get_card_in_hand(self, units_in_hand, select_ephemeral):
        if select_ephemeral:
            ephemerals = filter(lambda card_in_hand: "Ephemeral" in card_in_hand.keywords, units_in_hand)
            return next(ephemerals, units_in_hand[0])
        # select_ephemeral == False -> select the strongest
        return max(units_in_hand, key=lambda card_in_hand: card_in_hand.attack + card_in_hand.health)
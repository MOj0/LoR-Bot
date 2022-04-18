from time import sleep
from constants import GameState
from collections import defaultdict
from Strategy import Strategy

class Ephemeral(Strategy):
    def __init__(self, mouse_handler):
        super().__init__(mouse_handler)

        self.mulligan_cards = ("Zed", "Shark Chariot", "Shadow Fiend")
        self.graveyard = defaultdict(int)  # Counter of dead cards used for Harrowing
        self.spawn_on_attack = 0  # Increments when Shark Chariot dies
        self.hecarim_backed = False

    def block(self, cards_on_board, window_x, window_y, window_height):
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
            # Elusive and Fearsome check
            if "Elusive" in enemy_card.keywords or "Fearsome" in enemy_card.keywords and blocking_card.attack < 3:
                continue
            is_blockable = True
            # if "Ephemeral" in blocking_card.keywords or enemy_card.attack < blocking_card.health:  # Defensive block
            if "Ephemeral" in blocking_card.keywords or blocking_card.health == 1 or enemy_card.health <= blocking_card.attack:  # Aggressive block
                for ally_card in ally_cards:  # Check if card is already blocked
                    if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                        is_blockable = False
                        break
                if is_blockable:
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                    return True
        return False

    def playable_card(self, playable_cards, game_state, cards_on_board):
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

    def reorganize_attack(self, cards_on_board, window_x, window_y, window_height):
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
                self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], 100))
                return False

        # If attack would overflow
        if n_attackers + n_to_be_spawned > 6 and n_non_ephemeral > 0:
            for attack_card in cards_on_board["cards_attk"]:
                if "Ephemeral" not in attack_card.keywords and attack_card.get_name() != "Zed" and attack_card.get_name() != "Hecarim":
                    self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], 100))
                    return False

        # Position Hecarim to the right for max damage output
        if any(map(lambda attk_card: attk_card.get_name() == "Hecarim", cards_on_board["cards_attk"])) and not self.hecarim_backed :  # Retreat Hecarim from attack if it is on board
            for attack_card in cards_on_board["cards_attk"]:
                if attack_card.get_name() == "Hecarim":
                    self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0],  100))
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
        # Select the strongest
        return max(units_in_hand, key=lambda card_in_hand: card_in_hand.attack + card_in_hand.health)
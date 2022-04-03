from constants import GameState
from Strategy import Strategy

class Pirates(Strategy):
    def __init__(self, mouse_handler):
        super().__init__(mouse_handler)
        self.mulligan_cards = ("Crackshot Corsair", "Legion Rearguard",
                               "Legion Saboteur", "Precious Pet", "Prowling Cutthroat")

    def block(self, cards_on_board, window_x, window_y, window_height):
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

    def playable_card(self, playable_cards, game_state, cards_on_board):
        cards_sorted = sorted(playable_cards, key=lambda playable_card: playable_card.cost, reverse=True)
        n_cards_on_board = len(cards_on_board["cards_board"])
        for playable_card_in_hand in cards_sorted:
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

    def reorganize_attack(self, cards_on_board, window_x, window_y, window_height):
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        for attack_card in cards_on_board["cards_attk"]:
            # Remove Crackshot Corsair from board if necessary
            if attack_card.get_name() == "Crackshot Corsair" and len(cards_on_board["opponent_cards_board"]) != 0:
                self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], window_height - 100))
                return False

        return True
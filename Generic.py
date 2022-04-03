from constants import GameState
from Strategy import Strategy
from time import sleep


class Generic(Strategy):
    def __init__(self, mouse_handler):
        super().__init__(mouse_handler)

    def mulligan(self, cards, window_x, window_y, window_height):
        # Window stuff
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        # Mulligan away cards with cost greater than 3
        for in_game_card_obj in cards:
            if in_game_card_obj.cost > 3:
                cx = window_x + in_game_card_obj.top_center[0]
                cy = window_y + window_height - in_game_card_obj.top_center[1]
                self.mouse_handler.click(cx, cy)
                sleep(0.5)

    def block(self, cards_on_board, window_x, window_y, window_height):
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        for i, blocking_card in enumerate(cards_on_board["cards_board"]):
            if i < self.block_counter or "Can't Block" in blocking_card.keywords or "Immobile" in blocking_card.keywords:
                continue
            if self.blocked_with(blocking_card, cards_on_board["opponent_cards_attk"], cards_on_board["cards_attk"]):
                self.block_counter = (self.block_counter + 1) % len(cards_on_board["cards_board"])
                return True

        self.block_counter = 0
        return False

    def playable_card(self, playable_cards, game_state, cards_on_board):
        """Return the first playable highest cost card"""
        cards_sorted = sorted(playable_cards, key=lambda playable_card: playable_card.cost, reverse=True)
        n_cards_on_board = len(cards_on_board["cards_board"])
        for playable_card_in_hand in cards_sorted:
            n_summon = 2 if "summon a" in playable_card_in_hand.description_raw.lower() else 1
            if n_cards_on_board + n_summon > 6:
                continue
            if game_state == GameState.Attack_Turn or game_state == GameState.Defend_Turn:
                return playable_card_in_hand
        return None

    def reorganize_attack(self, cards_on_board, window_x, window_y, window_height):
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        # Remove cards with 0 attack power
        for attack_card in cards_on_board["cards_attk"]:
            if attack_card.attack == 0:
                self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], 100))
                return False

        return True

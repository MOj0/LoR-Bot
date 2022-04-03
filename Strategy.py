from time import sleep
from constants import GameState


class Strategy:
    def __init__(self, mouse_handler):
        self.window_x = 0
        self.window_y = 0
        self.window_height = 0
        self.block_counter = 0
        self.deck = None
        self.mouse_handler = mouse_handler

        # This will change in other constructors
        self.mulligan_cards = tuple()

    def set_deck(self, deck):
        self.deck = deck

    def drag_card_from_to(self, pos_src, pos_dest):
        pos_src = (self.window_x + pos_src[0], self.window_y + self.window_height - pos_src[1])
        pos_dest = (self.window_x + pos_dest[0], self.window_y + self.window_height - pos_dest[1])
        self.mouse_handler.hold(pos_src)
        self.mouse_handler.move_mouse_smooth(pos_dest[0], pos_dest[1])
        self.mouse_handler.release(pos_dest)
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
                self.mouse_handler.click(cx, cy)
                sleep(0.5)

    def play_card(self, card):
        (x, y) = (self.window_x + card.top_center[0], self.window_y + self.window_height - card.top_center[1])
        self.mouse_handler.move_mouse_smooth(x, y)
        sleep(0.5)  # Wait for the card maximize animation
        self.mouse_handler.hold(x, y)
        self.mouse_handler.move_mouse_smooth(x, int(y - 3 * self.window_height / 7))
        sleep(0.3)
        self.mouse_handler.release(x, int(y - 3 * self.window_height / 7))
        sleep(0.3)

    # Generic block, to be overriden by specific deck strategy
    def block(self, cards_on_board, window_x, window_y, window_height):
        # Window stuff
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

    # Generic blocked_with, to be overriden by specific deck strategy
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

    # To be overriden by the specific strategy
    def playable_card(self, playable_cards, game_state, cards_on_board):
        cards_sorted = sorted(playable_cards, key=lambda playable_card: 2 *
                              playable_card.attack + playable_card.cost, reverse=True)
        n_cards_on_board = len(cards_on_board["cards_board"])
        for playable_card_in_hand in cards_sorted:
            name = playable_card_in_hand.get_name()
            n_summon = 2 if "summon a" in playable_card_in_hand.description_raw.lower() else 1
            if n_cards_on_board + n_summon > 6 or all(card.get_name() != name for card in self.deck):
                continue
            if game_state == GameState.Attack_Turn or game_state == GameState.Defend_Turn:
                return playable_card_in_hand
        return None

    def reorganize_attack(self, cards_on_board, window_x, window_y, window_height) -> bool:
        """This method is called after 'a' key is pressed, until it returns True. To be overriden by specific strategies!"""
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        return True

    def get_card_in_hand(self, units_in_hand, select_ephemeral=False):
        # Select the strongest
        return max(units_in_hand, key=lambda card_in_hand: card_in_hand.attack + card_in_hand.health)

import cv2
import constants
import numpy as np
import keyboard
from time import sleep
from StateMachine import DeckType
from constants import GameState
from MouseHandler import MouseHandler

MANA_MASKS = (constants.ZERO, constants.ONE, constants.TWO, constants.THREE, constants.FOUR,
              constants.FIVE, constants.SIX, constants.SEVEN, constants.EIGHT, constants.NINE, constants.TEN)
NUM_PX_MASK = tuple(sum(val for line in mask for val in line) for mask in MANA_MASKS)


class Bot:
    """Plays the game, responisble for executing commands from DeckStrategy"""

    def __init__(self, state_machine, pvp=True):
        self.state_machine = state_machine
        self.pvp = pvp
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
        self.deck_strategy = None
        self.mana = 1
        self.prev_mana = 1
        self.spell_mana = 0
        self.turn = 1
        self.games_won = 0
        self.n_games = 0
        self.first_pass_blocking = False
        self.first_pass_spell = False
        self.mouse_handler = MouseHandler()

    def _get_mana(self, frames):
        # Magic
        mana_vals = tuple(i for image in frames for i, mask in enumerate(MANA_MASKS) if sum(map(bool, (val for edge, msk in zip(cv2.Canny(cv2.cvtColor(
            np.array(image.crop(box=(1585, 638, 1635, 675))), cv2.COLOR_BGR2GRAY), 100, 100), mask) for val in edge[msk]))) / NUM_PX_MASK[i] > 0.95)

        self.mana = mana_vals[0] if mana_vals else -1

    def run(self):
        while True:
            self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info()

            if isinstance(self.deck_type, DeckType) and self.deck_strategy is None:
                # Create a new DeckStrategy object from DeckType
                self.deck_strategy = self.deck_type.value(self.mouse_handler)
                if self.deck_strategy.deck is None and self.deck_type == DeckType.Pirates:
                    self.deck_strategy.set_deck(tuple(self.state_machine.get_deck()))

            if self.game_state == GameState.End:
                print("Game ended... waiting for animations")
                sleep(8)

                # Reset variables
                self.mana = self.prev_mana = self.turn = 1
                self.spell_mana = 0
                self.deck_strategy = None

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

            self.mouse_handler.move_mouse_smooth(self.window_x + self.window_width /
                                                 2, self.window_y + self.window_height/2)

    def continue_and_replay(self):
        sleep(4)
        continue_btn_pos = (self.window_x + 0.66 * self.window_width, self.window_y + self.window_height * 0.90)
        for _ in range(16):
            self.mouse_handler.click(continue_btn_pos)
            sleep(1.5)
        sleep(1)

    def is_state_playable(self) -> bool:
        if self.game_state == GameState.Hold:
            return False
        if self.game_state == GameState.Menus:
            print("Selecting deck")
            self.select_deck()
            sleep(5)
            return False
        if self.mana == -1:
            print("Unknown mana...")
            sleep(4)
            return False
        if self.mana > self.turn:  # New turn
            self.spell_mana = min(self.spell_mana + self.prev_mana, 3)
            self.turn = self.mana
            self.prev_mana = self.mana
            self.first_pass_blocking = self.first_pass_spell = False
            sleep(2)
            return False
        return True

    def play(self):
        in_game_cards = [card for cards in self.cards_on_board.values() for card in cards]

        if self.game_state == GameState.Mulligan:
            print("Thinking about mulligan...")
            sleep(10)

            # Get cards_on_board again, since they might have updated
            self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info(
                call_game_state=False)
            in_game_cards = [card for cards in self.cards_on_board.values() for card in cards]

            # Execute mulligan
            if self.deck_strategy:
                self.deck_strategy.mulligan(in_game_cards, self.window_x, self.window_y, self.window_height)

            print("Confirming mulligan")
            keyboard.send("space")

            sleep(8)
        elif self.game_state == GameState.Opponent_Turn:
            sleep(3)
            return
        elif self.game_state == GameState.Blocking:
            # Double check to avoid False Positives (card draw animation, card play animation...)
            if not self.first_pass_blocking:
                self.first_pass_blocking = True
                print("first blocking pass...")
                sleep(5)
                return

            block_counter = 0
            while block_counter < 12 and self.deck_strategy.block(self.cards_on_board, self.window_x, self.window_y, self.window_height):
                sleep(2)
                self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info(
                    call_game_state=False)

                block_counter += 1

            keyboard.send("space")
            sleep(10)
        elif self.game_state == GameState.Defend_Turn or self.game_state == GameState.Attack_Turn:
            if len(self.cards_on_board["spell_stack"]) != 0 and all((card.is_spell() or card.is_ability()) for card in self.cards_on_board["spell_stack"]):
                # Double check to avoid False Positives
                if not self.first_pass_spell:
                    self.first_pass_spell = True
                    print("first spell pass...")
                    sleep(12)
                    return
                keyboard.send("space")
                sleep(4)
                return
            playable_cards = sorted(filter(lambda card: card.cost <= self.mana or card.is_spell()
                                           and card.cost <= self.mana + self.spell_mana, self.cards_on_board["cards_hand"]), key=lambda card: card.cost, reverse=True)
            if len(playable_cards) == 0 and self.game_state == GameState.Attack_Turn or len(self.cards_on_board["cards_board"]) == 6:
                keyboard.send("a")

                # Sleep so API gets called again and get cards_on_board info
                sleep(1.25)
                self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info(
                    call_game_state=False)

                while not self.deck_strategy.reorganize_attack(self.cards_on_board, self.window_x, self.window_y, self.window_height):
                    sleep(1.25)
                    self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info(
                        call_game_state=False)

                keyboard.send("space")
            else:
                playable_card_in_hand = self.deck_strategy.playable_card(
                    playable_cards, self.game_state, self.cards_on_board)
                if playable_card_in_hand:
                    print("Playing card: ", playable_card_in_hand)
                    self.play_card(playable_card_in_hand)

                    # Grant/Pick an ally in hand mechanic
                    if "ally in hand" in playable_card_in_hand.description_raw:
                        sleep(1.25)
                        self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info(
                            call_game_state=False)
                        units_in_hand = tuple(
                            filter(lambda card_in_hand: not card_in_hand.is_spell(), self.cards_on_board["cards_attk"]))  # NOTE: Has to be cards_attk, because they are lifted
                        if units_in_hand:
                            select_epehemral = "Ephemeral" in playable_card_in_hand.description_raw
                            card_to_click = self.deck_strategy.get_card_in_hand(units_in_hand, select_epehemral)
                            self.mouse_handler.click(
                                self.window_x + card_to_click.top_center[0], self.window_y + self.window_height - card_to_click.top_center[1])
                    # Imperial Demolist play effect
                    elif "to an ally" in playable_card_in_hand.description_raw and len(self.cards_on_board["cards_board"]) != 0:
                        for card_to_click in self.cards_on_board["cards_board"]:
                            if card_to_click.health > 1:
                                self.mouse_handler.click(
                                    self.window_x + card_to_click.top_center[0], self.window_y + self.window_height - card_to_click.top_center[1])
                                sleep(0.5)
                                break
                        else:
                            keyboard.send("space")
                    elif playable_card_in_hand.get_name() == "Petty Officer":
                        sleep(0.75)
                        self.mouse_handler.click(self.window_x + 4 * self.window_width //
                                                 7, self.window_y + self.window_height // 2)
                        sleep(1)

                    if "Attune" in playable_card_in_hand.keywords:
                        self.spell_mana = min(3, self.spell_mana + 1)

                    # Calculate spell mana if necessary
                    if playable_card_in_hand.is_spell():
                        self.spell_mana = max(0, self.spell_mana - playable_card_in_hand.cost)

                    # Get new mana
                    sleep(1.25)
                    while True:
                        self._get_mana(self.state_machine.request_frames())
                        if self.mana != -1:
                            break
                    self.prev_mana = self.mana
                else:
                    if self.game_state == GameState.Attack_Turn:
                        keyboard.send("a")

                        # Sleep so API gets called again and get cards_on_board info
                        sleep(1.25)
                        self.game_state, self.cards_on_board, self.deck_type, self.n_games, self.games_won = self.state_machine.get_game_info(
                            call_game_state=False)
                        sleep(1)

                    keyboard.send("space")
        sleep(4)

    def play_card(self, card):
        (x, y) = (self.window_x + card.top_center[0], self.window_y + self.window_height - card.top_center[1])
        self.mouse_handler.move_mouse_smooth(x, y)
        sleep(0.5)  # Wait for the card maximize animation
        self.mouse_handler.hold(x, y)
        self.mouse_handler.move_mouse_smooth(x, int(y - 3 * self.window_height / 7))
        sleep(0.3)
        self.mouse_handler.release(x, int(y - 3 * self.window_height / 7))
        sleep(0.3)
        if card.is_spell():
            sleep(1)
            keyboard.send("space")

    def select_deck(self):
        vals_ai = [(0.04721, 0.33454), (0.15738, 0.33401), (0.33180, 0.30779), (0.83213, 0.89538), (0.73645, 0.92129)]
        vals_pvp = [(0.04721, 0.33454), (0.15738, 0.25), (0.33180, 0.30779), (0.83213, 0.89538)]
        vals = vals_pvp if self.pvp else vals_ai
        for val in vals:
            v = (self.window_x + val[0] * self.window_width, self.window_y + val[1] * self.window_height)
            self.mouse_handler.click(int(v[0]), int(v[1]))
            sleep(0.7)

        sleep(1)
        # Handle "Matchmaking has failed" error
        ok_button_pos = (self.window_x + 0.5 * self.window_width, self.window_y + 0.546 * self.window_height)
        self.mouse_handler.click(int(ok_button_pos[0]), int(ok_button_pos[1]))

    def get_display_data(self) -> dict:
        return {"game_state": self.game_state, "cards_on_board": self.cards_on_board, "deck_type": self.deck_type, "mana": self.mana,
                "spell_mana": self.spell_mana, "prev_mana": self.prev_mana, "games_won": self.games_won,
                "n_games": self.n_games, "turn": self.turn}

    def get_window_info(self) -> tuple:
        # return self.window_info
        return tuple((self.window_x, self.window_y, self.window_width, self.window_height))

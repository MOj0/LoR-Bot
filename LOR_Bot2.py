import cv2
from termcolor import colored
import threading
import numpy as np
import keyboard
from time import sleep
from APICaller import APICaller
from Bot import Bot
from StateMachine import StateMachine
from StateMachine import DeckType, GameState

FONT = cv2.FONT_HERSHEY_SIMPLEX

state_machine = StateMachine()

bot = Bot(state_machine, is_vs_ai=True)
bot_thread = threading.Thread(target=bot.run)
bot_thread.daemon = True
bot_thread.start()

sleep(0.1) # Necessary if we want to call get_window_info_frames now

if state_machine.get_window_info_frames()[0][:2] == (-1, -1):  # Only check if x and y coords are -1
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)

# TODO: Ephemeral deck improvements:
# GRAVEYARD (retreat weakest units from attack if units from graveyard will spawn in), 
# Position Hecarim to right for max damage,
# Retreat Soul Shepard from attack if there is a threat on enemy board (any unit with more or equal than 3 attack)

api_caller = APICaller()
api_thread = threading.Thread(target=api_caller.call_api)
api_thread.daemon = True
api_thread.start()

while True:
    state_machine.set_game_data(api_caller.get_game_data())
    state_machine.set_cards_data(api_caller.get_cards_data())
    state_machine.set_game_result(api_caller.get_game_result())
    
    display_data = bot.get_display_data()  # Also contains data from state_machine

    shape = (720, 1280)
    background_color = (0.0, 0.4, 0.1) if keyboard.is_pressed("ctrl") else (0.0, 0.0, 0.0)
    board_state_img = np.full((*shape, len(background_color)), background_color)
    game_state_str = "(Unknown)" if not isinstance(
        display_data["game_state"], GameState) else display_data["game_state"].name
    deck_type_str = "(No deck selected)" if not isinstance(
        display_data["deck_type"], DeckType) else display_data["deck_type"].name

    board_state_img = cv2.putText(board_state_img, deck_type_str, (500, 100), FONT, 1, (255, 255, 255), 2)
    board_state_img = cv2.putText(board_state_img, game_state_str, (1000, 40), FONT, 1, (0, 255, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Round {}".format(display_data["turn"]),
                                  (1000, 80), FONT, 1, (0, 255, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Mana {}".format(display_data["mana"]),
                                  (1000, 120), FONT, 1, (0, 20, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Spell mana {}".format(display_data["spell_mana"]),
                                  (1000, 160), FONT, 1, (0, 100, 255), 2)
    board_state_img = cv2.putText(board_state_img, "Prev mana {}".format(display_data["prev_mana"]),
                                  (1000, 200), FONT, 1, (0, 100, 255), 2)
    board_state_img=cv2.putText(board_state_img, "Win% {}/{} ({})".format(
        display_data["games_won"], display_data["n_games"], ("/" if display_data["n_games"] == 0 else str(100 * display_data["games_won"] / display_data["n_games"])) + " %"),
        (1000, 240), FONT, 1, (0, 255, 255), 2)

    # WORKAROUND: tuple for display_data so it doesn't change during iteration
    for i, (position, cards) in enumerate(tuple(display_data["cards_on_board"].items())):
        board_state_img=cv2.putText(board_state_img, position, (20, 30 + 150 * i), FONT, 1, (0, 255, 0), 2)
        for j, card in enumerate(cards):
            board_state_img=cv2.putText(board_state_img, card.get_name(
            ), (20, 50 + 150 * i + 25 * j), FONT, 1, (255, 0, 0), 2)

    # Show board state
    cv2.imshow('Board state', board_state_img)

    # Quit condition
    if cv2.waitKey(20) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break

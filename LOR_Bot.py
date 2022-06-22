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
import sys
from download_card_sets import download_missing_card_sets, is_card_set_missing

FONT = cv2.FONT_HERSHEY_SIMPLEX
state_machine = StateMachine()

if is_card_set_missing():
    background_info = np.full((*(720, 1280), 3), (0.0, 0.0, 0.0))
    download_str1 = "Downloading missing card sets..."
    download_str2 = "This might take a while and the application might seem unresponsive"
    background_info = cv2.putText(background_info, download_str1, (250, 100), FONT, 1, (255, 255, 255), 2)
    background_info = cv2.putText(background_info, download_str2, (100, 200), FONT, 1, (255, 255, 255), 2)
    cv2.imshow('Downloading card sets...', background_info)
    cv2.waitKey(1)

    download_missing_card_sets()
    cv2.destroyAllWindows()

isPvp = len(sys.argv) != 2 or sys.argv[-1] != "noPVP"
print("PvP Mode" if isPvp else "Playing against AI...")

bot = Bot(state_machine, pvp=isPvp)
bot_thread = threading.Thread(target=bot.run)
bot_thread.daemon = True
bot_thread.start()

sleep(0.1)  # Necessary if we want to call get_window_info_frames now

if state_machine.get_window_info_frames()[0][:2] == (-1, -1):  # Only check if x and y coords are -1
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)


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
    background_color = (0.6, 0.1, 0.1) if keyboard.is_pressed("ctrl") else (0.0, 0.0, 0.0)
    background_info = np.full((*shape, len(background_color)), background_color)
    download_str1 = "(Unknown)" if not isinstance(
        display_data["game_state"], GameState) else display_data["game_state"].name
    deck_type_str = "(No deck selected)" if not isinstance(
        display_data["deck_type"], DeckType) else display_data["deck_type"].name

    background_info = cv2.putText(background_info, deck_type_str, (500, 100), FONT, 1, (255, 255, 255), 2)
    background_info = cv2.putText(background_info, download_str1, (1000, 40), FONT, 1, (0, 255, 255), 2)
    background_info = cv2.putText(background_info, "Round {}".format(display_data["turn"]),
                                  (850, 80), FONT, 1, (0, 255, 255), 2)
    background_info = cv2.putText(background_info, "Mana {}".format(display_data["mana"]),
                                  (850, 120), FONT, 1, (0, 20, 255), 2)
    background_info = cv2.putText(background_info, "Spell mana {}".format(display_data["spell_mana"]),
                                  (850, 160), FONT, 1, (0, 100, 255), 2)
    background_info = cv2.putText(background_info, "Prev mana {}".format(display_data["prev_mana"]),
                                  (850, 200), FONT, 1, (0, 100, 255), 2)
    background_info = cv2.putText(background_info, "Win% {}/{} ({})".format(
        display_data["games_won"], display_data["n_games"], ("/" if display_data["n_games"] == 0 else str(100 * display_data["games_won"] / display_data["n_games"])) + " %"),
        (850, 240), FONT, 1, (0, 255, 255), 2)

    # WORKAROUND: tuple for display_data so it doesn't change during iteration
    for i, (position, cards) in enumerate(tuple(display_data["cards_on_board"].items())):
        background_info = cv2.putText(background_info, position, (20, 30 + 150 * i), FONT, 1, (0, 255, 0), 2)
        for j, card in enumerate(cards):
            background_info = cv2.putText(background_info, card.get_name(
            ), (20, 50 + 150 * i + 25 * j), FONT, 1, (255, 0, 0), 2)

    # Show board state
    cv2.imshow('Board state', background_info)

    # Quit condition
    if cv2.waitKey(20) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break

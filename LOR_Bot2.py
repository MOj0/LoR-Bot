import cv2
from termcolor import colored
import threading
from time import sleep
from APICaller import APICaller
from Bot import Bot

font = cv2.FONT_HERSHEY_SIMPLEX
font_color = (0, 0, 255)

bot = Bot(is_vs_ai=True)
bot_thread = threading.Thread(target=bot.start)
bot_thread.daemon = True
bot_thread.start()

api_caller = APICaller()
api_thread = threading.Thread(target=api_caller.call_api)
api_thread.daemon = True
api_thread.start()

sleep(0.1)  # Necessary for threads to actually start!

if bot.get_window_info()[:2] == [-1, -1]:
    print(colored("Legends of Runeterra isn't running!", "red"))
    exit(1)

# while True:
    # print(bot.get_window_info())
#     bot.set_game_data(api_caller.get_game_data())
#     bot.set_cards_data(api_caller.get_cards_data())
#     bot.set_game_result(api_caller.get_game_result())

#     display_data = bot.get_display_data()

#     shape = (720, 1280)
#     background_color = (0.0, 0.4, 0.1) if display_data["game_state"] == "(HOLD)" else (0.0, 0.0, 0.0)
#     board_state_img = np.full((*shape, len(background_color)), background_color)
#     board_state_img = cv2.putText(board_state_img, display_data["deck_type"], (500, 100), font, 1, (255, 255, 255), 2)
#     board_state_img = cv2.putText(board_state_img, "{}".format(display_data["game_state"]),
#                                   (1000, 40), font, 1, (0, 255, 255), 2)
#     board_state_img = cv2.putText(board_state_img, "Round {}".format(display_data["turn"]),
#                                   (1000, 80), font, 1, (0, 255, 255), 2)
#     board_state_img = cv2.putText(board_state_img, "Mana {}".format(display_data["mana"]),
#                                   (1000, 120), font, 1, (0, 20, 255), 2)
#     board_state_img = cv2.putText(board_state_img, "Spell mana {}".format(display_data["spell_mana"]),
#                                   (1000, 160), font, 1, (0, 100, 255), 2)
#     board_state_img = cv2.putText(board_state_img, "Prev mana {}".format(display_data["prev_mana"]),
#                                   (1000, 200), font, 1, (0, 100, 255), 2)
#     board_state_img = cv2.putText(board_state_img, "Win% {}/{} ({})".format(
#         display_data["games_won"], display_data["n_games"], ("/" if display_data["n_games"] == 0 else str(display_data["games_won"] / display_data["n_games"])) + " %"),
#         (1000, 240), font, 1, (0, 255, 255), 2)

#     for i, (position, cards) in enumerate(display_data["board_state"].items()):
#         board_state_img = cv2.putText(board_state_img, position, (20, 30 + 150 * i), font, 1, (0, 255, 0), 2)
#         for j, card in enumerate(cards):
#             board_state_img = cv2.putText(board_state_img, card.get_name(
#             ), (20, 50 + 150 * i + 25 * j), font, 1, (255, 0, 0), 2)

#     # Show board state
#     cv2.imshow('Board state', board_state_img)

#     # Quit condition
#     if cv2.waitKey(20) & 0xFF == ord('q'):
#         cv2.destroyAllWindows()
#         break

# Legends of Runeterra Bot

A bot for the game [Legends of Runeterra](https://playruneterra.com/en-us/) written in Python. It can play the game on a very superficial level.

<p align="center">
  <img src="gifs/demo.gif"/>
</p>

# Prerequisites

- Python 3 (tested on `Python 3.10.2`)
- All libraries in `requirements.txt` installed (run `pip install -r requirements.txt`)
- Game running fullscreen at **1920x1080** resolution and at least **medium** quality, with display scaling set to 100% (otherwise the image detection procedure cannot read the mana values)
- In-game third party endpoints enabled on port 21337 (should be on by default)

If you encounter a problem where the script keeps reporting "Unknown mana", take a look at [this issue](https://github.com/MOj0/LoR-Bot/issues/22).

# Notes

In case you get a `Warning: card with key: [card_key] not found.` you can delete the `card_sets` folder and restart the program. In case it still does not work, it might be because Riot decided not to make all cards publicly available (I am guessing some special skills), and there is nothing I can do about it. Although bot won't recognize all cards in that case, it should still play just fine.

This bot is very limited in terms of functionality:

- Every information about a card (apart from its position) is **static**, which means it **does not consider unit's change in stats** (attack, health, mana, additional keywords ...)
- **It does not know how to do targeting at all** (apart from few exceptions: Imperial Demolitionist, Oblivious Islander)

# Decks

There are 2 variations of a Bilgewater/Noxus aggro deck, which managed to reach **Masters**.
[Screenshots here](https://github.com/MOj0/LoR-Bot/issues/21#issuecomment-1583795146).

- **Master (79): CICACBIGAEBAEAYEAUBQEBQWFU6AMAIDAIGA6JJGFABACAIDDYAQEBQIAA**
- **Master (35): CICACAQDAQAQKBQBAUAQGAQMEUTCQBICAYEBMJRNHQAQEAIDA4NAA**

Here are also some of my decks:

- **Ephemeral: CEBQCBACBYBQCAQJBUNQSAIFAMCAOCQMCULSMKQAAEAQCBJB**
- **Pirates: CICACAQDAQAQKBQBAUAQGAQMB4SSQBICAYLCAJRNHQAQEAQGBAGQA**
- **Mistwraiths: CEBQCBAFGYBQGBIDAYGQQAIFAMHBAHRBE42TQAQBAEBTGAIBAU3QA**

Note that this bot has built-in strategies (play styles) for Ephemeral and Pirate decks, which are determined automatically. If the deck isn't recognized, it will switch to **generic** play style.

# How to run

Run the game the way it is specified in the Prerequisites section and run the following command in the project directory: `python LOR_Bot.py` or simply use your IDE to run that file. If you want to test the bot against the in-game AI, you can run: `python LOR_Bot.py noPVP`

A new window should open containing various information about the current state of the game.

Bot will then navigate through menus and **always select the first deck in your collection** and select the play button. You can favorite the deck you want to use, or prepend the deck's name with a '.' (that way it will appear first on the list).

If you would like to **obtain control** of your mouse, **hold down the `Ctrl` key**. It may not work instantly, but it will stop in time.

If you would like to **quit** the application, you can press the **`Q` key** on the opened window or press the `Ctrl-C` combination in the terminal.

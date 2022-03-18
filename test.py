from enum import Enum
from Ephemeral import Ephemeral
from Aggro import Aggro

class DeckType(Enum):
    Ephemeral = Ephemeral
    Aggro = Aggro


dummy = DeckType
deck_type = DeckType.Ephemeral
# deck = deck_type.value()

print(dummy)
print(deck_type)

print(isinstance(None, DeckType))
print(isinstance(dummy, DeckType))
print(isinstance(deck_type, DeckType))
# print(deck)
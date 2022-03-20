class Card:
    def __init__(self, name, cost, attack, health, type, keywords):
        self.name = name
        self.cost = cost
        self.attack = attack
        self.health = health
        self.type = type
        self.keywords = keywords

    def __str__(self):
        return "Card({} ({}) T: {} A: {} H: {})".format(self.name, self.cost, self.type, self.attack, self.health)

    def get_name(self):
        return self.name

    def is_spell(self) -> bool:
        return self.type == "Spell"


class InGameCard(Card):
    def __init__(self, card, x, y, w, h, is_local):
        super().__init__(card.name, card.cost, card.attack, card.health, card.type, card.keywords)
        self.top_center = (int(x + w / 2), int(y - h / 4))
        self.is_local = is_local

    def __str__(self):
        return "InGameCard({} -- top_center:({}); is_local:{})".format(super().__str__(), self.top_center, self.is_local)

    def get_pos(self):
        return self.top_center

from dataclasses import dataclass
import random

SUITS = [0, 1, 2, 3]   # H, D, C, S
RANKS = list(range(1, 14))  # A(1) .. K(13)
@dataclass
class Card:
    rank: int   # 1-13
    suit: int   # 0-3

def card_value(card: Card) -> int:
    if card.rank >= 11:       # J, Q, K
        return 10
    else:
        return card.rank        # 2-10

class Deck:
    def __init__(self):
        self.cards = [Card(r, s) for r in RANKS for s in SUITS]
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            raise RuntimeError("Deck is empty")
        return self.cards.pop()




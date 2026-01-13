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

def dealer_turn(deck: Deck, dealer_cards: list) -> tuple[list, int, bool]:
    """
    Executes dealer logic.
    
    Returns:
        dealer_cards: final list of cards
        dealer_total: final sum
        dealer_bust: True if sum > 21
    """
    dealer_total = sum(card_value(c) for c in dealer_cards)

    while dealer_total < 17:
        card = deck.draw()
        dealer_cards.append(card)
        dealer_total += card_value(card)

    dealer_bust = dealer_total > 21
    return dealer_cards, dealer_total, dealer_bust

def decide_winner(client_total: int, dealer_total: int,
                  client_bust: bool, dealer_bust: bool) -> int:
    """
    Returns result code:
    0x3 → client win
    0x2 → client loss
    0x1 → tie
    """

    if client_bust:
        return 0x2  # loss
    if dealer_bust:
        return 0x3  # win

    if client_total > dealer_total:
        return 0x3
    if dealer_total > client_total:
        return 0x2
    return 0x1



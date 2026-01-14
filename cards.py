import struct

# ANSI Color Codes
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

SUITS = {
    0: 'Hearts',  # Red
    1: 'Diamonds',  # Red
    2: 'Clubs',  # Green (Real cards are Black, but Green is visible)
    3: 'Spades'  # Blue (Real cards are Black, but Blue is visible)
}

RANKS = {
    1: 'Ace', 2: '2', 3: '3', 4: '4', 5: '5',
    6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
    11: 'Jack', 12: 'Queen', 13: 'King'
}


def decode_card(card_bytes):
    """
    Decodes the 3-byte card data into a colored string.
    """
    if len(card_bytes) != 3:
        return "Unknown Card"

    try:
        rank_val, suit_val = struct.unpack('!HB', card_bytes)

        rank_str = RANKS.get(rank_val, str(rank_val))
        suit_str = SUITS.get(suit_val, 'Unknown Suit')

        # Color logic
        color = RESET
        if suit_val == 0 or suit_val == 1:  # Hearts & Diamonds
            color = RED
        elif suit_val == 2:  # Clubs
            color = GREEN
        elif suit_val == 3:  # Spades
            color = BLUE

        return f"{color}{rank_str} of {suit_str}{RESET}"

    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return f"Corrupted Card ({card_bytes.hex()})"


def calculate_hand_total(ranks_list):
    """
    Calculates the total. Ace (1) is always 1. Face cards are 10.
    """
    total = 0
    for rank in ranks_list:
        if rank >= 10:  # Jack, Queen, King
            total += 10
        else:
            # Ace(1) .. 9 are just their face value
            total += rank

    return total
from dataclasses import dataclass
import random

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




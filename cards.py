import struct

# Suits mapping: 0-3 correspond to Hearts, Diamonds, Clubs, Spades
SUITS = {
    0: 'Hearts',
    1: 'Diamonds',
    2: 'Clubs',
    3: 'Spades'
}

# Ranks mapping: 1-13
RANKS = {
    1: 'Ace', 2: '2', 3: '3', 4: '4', 5: '5',
    6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
    11: 'Jack', 12: 'Queen', 13: 'King'
}


def decode_card(card_bytes):
    """
    Decodes the 3-byte card data from the server into a readable string.
    [cite_start]Format[cite: 103]:
    - First 2 bytes: Rank (1-13)
    - Next 1 byte: Suit (0-3)
    """
    if len(card_bytes) != 3:
        return "Unknown Card"

    try:
        # Unpack: H = unsigned short (2 bytes), B = unsigned char (1 byte)
        # Use ! for Network Byte Order (Big Endian)
        rank_val, suit_val = struct.unpack('!HB', card_bytes)

        rank_str = RANKS.get(rank_val, str(rank_val))
        suit_str = SUITS.get(suit_val, 'Unknown Suit')

        return f"{rank_str} of {suit_str}"

    except Exception as e:
        return f"Corrupted Card ({card_bytes.hex()})"
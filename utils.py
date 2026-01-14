UDP_PORT = 13122 # listening port for UDP offers (Hardcoded per instructions)
BUFFER_SIZE = 1024
MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2     # Byte value indicating the packet is a Server Offer.
MSG_TYPE_REQUEST = 0x3   # Byte value indicating the packet is a Client Request.
MSG_TYPE_PAYLOAD = 0x4   # Byte value indicating the packet is a Game Payload (move/result).

CMD_HIT = "Hittt"
CMD_STAND = "Stand"

RESULT_ACTIVE = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3
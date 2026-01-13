import struct
import socket
import time
import threading
import random
from dataclasses import dataclass

SUITS = [0, 1, 2, 3]   # H, D, C, S
RANKS = list(range(1, 14))  # A(1) .. K(13)

LISTEN_BACKLOG = 5
TCP_BIND_ADDR = ''  # all interfaces

MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2

BROADCAST_PORT = 13122
BROADCAST_INTERVAL = 1.0  # seconds
BROADCAST_ADDR = '<broadcast>'
OFFER_STRUCT = "!IBH32s"
SERVER_PAYLOAD_STRUCT = "!IBBHB"
CLIENT_PAYLOAD_STRUCT = "!IB5s"
MSG_TYPE_PAYLOAD = 0x4
# Decisions
DECISION_HIT = b"Hittt"
DECISION_STAND = b"Stand"

# Results
RESULT_NOT_OVER = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

def udp_offer_broadcast_loop(tcp_port: int, server_name: str):
    offer_packet = build_offer_packet(tcp_port, server_name)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Allow broadcast
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Allow reuse (important during testing)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print("Server started, broadcasting offers...")

    try:
        while True:
            sock.sendto(offer_packet, (BROADCAST_ADDR, BROADCAST_PORT))
            time.sleep(BROADCAST_INTERVAL)  # blocks → no busy waiting

    except KeyboardInterrupt:
        print("\nServer shutting down (broadcast loop stopped).")

    finally:
        sock.close()

def client_handler(client_sock: socket.socket, client_addr):
    try:
        client_sock.settimeout(10)

        # Placeholder: just receive something
        data = client_sock.recv(1024)
        if not data:
            return

        print(f"Received {len(data)} bytes from {client_addr}")

    except socket.timeout:
        print(f"Client {client_addr} timed out")

    except Exception as e:
        print(f"Error with client {client_addr}: {e}")

    finally:
        client_sock.close()
        print(f"Connection closed: {client_addr}")

def tcp_accept_loop(tcp_port: int, client_handler):
    """
    Accepts incoming TCP connections forever.
    For each client, starts a new handler thread.
    """

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_sock.bind((TCP_BIND_ADDR, tcp_port))
    server_sock.listen(LISTEN_BACKLOG)

    print(f"TCP server listening on port {tcp_port}")

    try:
        while True:
            client_sock, client_addr = server_sock.accept()
            print(f"New client connected from {client_addr}")

            thread = threading.Thread(
                target=client_handler,
                args=(client_sock, client_addr),
                daemon=True
            )
            thread.start()

    except KeyboardInterrupt:
        print("\nTCP server shutting down.")

    finally:
        server_sock.close()

def parse_client_payload(data: bytes) -> str:
    if len(data) != 10:
        raise ValueError("Invalid client payload length")

    magic, msg_type, decision = struct.unpack(CLIENT_PAYLOAD_STRUCT, data)

    if magic != MAGIC_COOKIE:
        raise ValueError("Bad magic cookie")
    if msg_type != MSG_TYPE_PAYLOAD:
        raise ValueError("Bad message type")

    decision = decision.decode('ascii')

    if decision not in ("Hittt", "Stand"):
        raise ValueError("Invalid decision value")

    return decision

# def build_server_payload(result: int, card=None) -> bytes:
#     """
#     card: Card or None
#     If round is not over, card must be provided.
#     If round is over, rank/suit should be 0.
#     """
#     if card:
#         rank, suit = card.rank, card.suit
#     else:
#         rank, suit = 0, 0

#     return struct.pack(
#         SERVER_PAYLOAD_STRUCT,
#         MAGIC_COOKIE,
#         MSG_TYPE_PAYLOAD,
#         result,
#         rank,
#         suit
#     )

def parse_client_payload(data: bytes) -> str:
    if len(data) != 10:
        raise ValueError("Invalid client payload length")

    magic, msg_type, decision = struct.unpack(CLIENT_PAYLOAD_STRUCT, data)

    if magic != MAGIC_COOKIE:
        raise ValueError("Bad magic cookie")
    if msg_type != MSG_TYPE_PAYLOAD:
        raise ValueError("Bad message type")

    decision = decision.decode('ascii')

    if decision not in ("Hittt", "Stand"):
        raise ValueError("Invalid decision value")

    return decision

if __name__ == "__main__":
    TCP_PORT = 2048
    SERVER_NAME = "DealerOfri"

    # Start UDP broadcast in background
    udp_thread = threading.Thread(
        target=udp_offer_broadcast_loop,
        args=(TCP_PORT, SERVER_NAME),
        daemon=True
    )
    udp_thread.start()

    # Run TCP accept loop (blocks forever)
    tcp_accept_loop(TCP_PORT, client_handler)
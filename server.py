import struct
import socket
import time
import threading
from cards import Card, card_value, Deck
from utils import MAGIC_COOKIE, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD
from utils import CMD_HIT, CMD_STAND
from utils import RESULT_ACTIVE, RESULT_TIE, RESULT_LOSS, RESULT_WIN
from utils import UDP_PORT

LISTEN_BACKLOG = 5
TCP_BIND_ADDR = ''  # all interfaces

BROADCAST_INTERVAL = 1.0  # seconds
BROADCAST_ADDR = '<broadcast>'
OFFER_STRUCT = "!IBH32s"
REQUEST_STRUCT = "!IBB32s"
MAX_ROUNDS = 255
REQUEST_SIZE = 38
SERVER_PAYLOAD_STRUCT = "!IBBHB"
CLIENT_PAYLOAD_STRUCT = "!IB5s"


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
        return RESULT_LOSS  # loss
    if dealer_bust:
        return RESULT_WIN  # win

    if client_total > dealer_total:
        return RESULT_WIN
    if dealer_total > client_total:
        return RESULT_LOSS
    return RESULT_TIE


def build_offer_packet(tcp_port: int, server_name: str) -> bytes:
    name_bytes = server_name.encode('utf-8')
    name_bytes = name_bytes[:32].ljust(32, b'\x00')

    return struct.pack(
        OFFER_STRUCT,
        MAGIC_COOKIE,
        MSG_TYPE_OFFER,
        tcp_port,
        name_bytes
    )

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
            sock.sendto(offer_packet, (BROADCAST_ADDR, UDP_PORT))
            time.sleep(BROADCAST_INTERVAL)  # blocks → no busy waiting

    except KeyboardInterrupt:
        print("\nServer shutting down (broadcast loop stopped).")

    finally:
        sock.close()


class RequestParseError(Exception):
    pass


def parse_request_packet(data: bytes):
    """
    Parses a client request packet.

    Returns:
        rounds (int)
        team_name (str)

    Raises:
        RequestParseError on any validation failure.
    """

    if len(data) != REQUEST_SIZE:
        raise RequestParseError("Invalid request length")

    try:
        magic, msg_type, rounds, name_bytes = struct.unpack(REQUEST_STRUCT, data)
    except struct.error:
        raise RequestParseError("Struct unpack failed")

    if magic != MAGIC_COOKIE:
        raise RequestParseError("Bad magic cookie")

    if msg_type != MSG_TYPE_REQUEST:
        raise RequestParseError("Bad message type")

    if rounds == 0 or rounds > MAX_ROUNDS:
        raise RequestParseError("Invalid number of rounds")

    team_name = name_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')

    if not team_name:
        raise RequestParseError("Empty team name")

    return rounds, team_name


def client_handler(client_sock: socket.socket, client_addr):
    try:
        client_sock.settimeout(30)
        game_loop(client_sock)

    except (ConnectionError, socket.timeout):
        print(f"Client {client_addr} disconnected")

    except Exception as e:
        print(f"Error with client {client_addr}: {e}")

    finally:
        client_sock.close()

def recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Client disconnected")
        data += chunk
    return data

def game_loop(client_sock: socket.socket):
    """
    Full server-side blackjack game loop for one client.
    """

    # ---- Receive request ----
    data = recv_exact(client_sock, REQUEST_SIZE)
    rounds, team_name = parse_request_packet(data)

    try:
        client_sock.recv(1)
    except:
        pass

    print(f"Client '{team_name}' connected, playing {rounds} rounds")
    games_won = 0

    for round_num in range(1, rounds + 1):
        try:
            print(f"Starting round {round_num}")

            deck = Deck()

            # ---- Initial deal ----
            client_cards = [deck.draw(), deck.draw()]
            dealer_cards = [deck.draw(), deck.draw()]

            client_total = sum(card_value(c) for c in client_cards)
            dealer_total = card_value(dealer_cards[0])  # second card hidden

            # Send dealer's visible card
            client_sock.sendall(
                build_server_payload(RESULT_ACTIVE, dealer_cards[0])
            )
            
            # Send client cards
            for card in client_cards:
                payload = build_server_payload(RESULT_ACTIVE, card)
                client_sock.sendall(payload)

            client_bust = False

            # ---- Player turn ----
            while True:
                if client_total > 21:
                    client_bust = True
                    break

                data = recv_exact(client_sock, 10)
                decision = parse_client_payload(data)

                if decision == CMD_STAND:
                    break

                elif decision == CMD_HIT:
                    # Hit
                    card = deck.draw()
                    client_cards.append(card)
                    client_total += card_value(card)

                    client_sock.sendall(
                        build_server_payload(RESULT_ACTIVE, card)
                    )
                else:
                    raise ValueError("Invalid client decision")

            # ---- Dealer turn ----
            dealer_bust = False

            if not client_bust:
                # Reveal hidden dealer card
                client_sock.sendall(
                    build_server_payload(RESULT_ACTIVE, dealer_cards[1])
                )

                dealer_cards, dealer_total, dealer_bust = dealer_turn(
                    deck, dealer_cards
                )

                # Send any additional dealer cards
                for card in dealer_cards[2:]:
                    client_sock.sendall(
                        build_server_payload(RESULT_ACTIVE, card)
                    )

            # ---- Decide winner ----
            result = decide_winner(
                client_total,
                dealer_total,
                client_bust,
                dealer_bust
            )
            if result == RESULT_WIN:
                games_won += 1

            # ---- Send final result ----
            client_sock.sendall(
                build_server_payload(result, None)
            )

            print(f"Client '{team_name}' finished all rounds, won {games_won}/{round_num} games")

        except (BrokenPipeError, ConnectionResetError, ConnectionError):
            print(f"Client '{team_name}' disconnected mid-round")
            return
        

def tcp_accept_loop(tcp_port: int, client_handler):
    """
    Accepts incoming TCP connections forever.
    For each client, starts a new handler thread.
    """
    # Creates and sets up the TCP server socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((TCP_BIND_ADDR, tcp_port))
    server_sock.listen(LISTEN_BACKLOG)

    print(f"TCP server listening on port {tcp_port}")

    # Accept loop
    try:
        while True:
            client_sock, client_addr = server_sock.accept()
            print(f"New client connected from {client_addr}")
            # Start a new thread to handle the client
            thread = threading.Thread(
                target=client_handler,
                args=(client_sock, client_addr),
                daemon=True
            )
            thread.start()
    except socket.timeout:
        print(f"Client {client_addr} timed out during game")
    
    except KeyboardInterrupt:
        print("\nTCP server shutting down.")

    finally:
        server_sock.close()

def build_server_payload(result: int, card: Card = None) -> bytes:
    """
    card: Card or None
    If round is not over, card must be provided.
    If round is over, rank/suit should be 0.
    """
    if card:
        rank, suit = card.rank, card.suit
    else:
        rank, suit = 0, 0

    return struct.pack(
        SERVER_PAYLOAD_STRUCT,
        MAGIC_COOKIE,
        MSG_TYPE_PAYLOAD,
        result,
        rank,
        suit
    )

def parse_client_payload(data: bytes) -> str:
    if len(data) != 10:
        raise ValueError("Invalid client payload length")
    magic, msg_type, decision = struct.unpack(CLIENT_PAYLOAD_STRUCT, data)
    
    # Validate the data
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
    SERVER_NAME = "Chauncey Billups"

    # Start UDP broadcast in background
    udp_thread = threading.Thread(
        target=udp_offer_broadcast_loop,
        args=(TCP_PORT, SERVER_NAME),
        daemon=True
    )
    udp_thread.start()

    # Run TCP accept loop (blocks forever)
    tcp_accept_loop(TCP_PORT, client_handler)
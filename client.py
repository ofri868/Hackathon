import socket
import struct
import time

UDP_PORT = 13122 # listening port for UDP offers (Hardcoded per instructions)
BUFFER_SIZE = 1024
MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2     # Byte value indicating the packet is a Server Offer.
MSG_TYPE_REQUEST = 0x3   # Byte value indicating the packet is a Client Request.
MSG_TYPE_PAYLOAD = 0x4   # Byte value indicating the packet is a Game Payload (move/result).

class Client:
    def __init__(self):
        self.server_ip = None
        self.server_port = None
        self.player_name = "Team Avdija"

    def listen_for_offers(self):
        print(f"Client started, listening for offer requests...")

        # 1. Create UDP socket, use IPv4 and datagram protocol for UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # SO_REUSEADDR = This allows us to restart the program and re-bind to port 13122 immediately
        # without waiting for the OS to release the port (prevents "Address already in use" errors).
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Good for restarts

        sock.bind(("", UDP_PORT))

        while True:
            try:
                #blocking call
                data, addr = sock.recvfrom(BUFFER_SIZE)
                # Packet format: [Magic Cookie 4B] [Type 1B] [Server Port 2B] [Server Name 32B]
                print(f"Received offer from {addr[0]}, attempting to parse...")
                if self._parse_offer(data):
                    self.server_ip = addr[0]
                    # Once we have a valid offer, we break to connect
                    break

            except Exception as e:
                print(f"Error receiving offer: {e}")

        sock.close()

    def _parse_offer(self, data):
        """
        Validates the offer packet and extracts server details.
        Returns True if the packet is valid, False otherwise.
        """
        try:
            # The packet must be at least 39 bytes long (4 + 1 + 2 + 32).
            if len(data) < 39:
                return False

            # struct.unpack converts raw bytes back into Python variables.
            # '!IBH32s' is the format string:
            #   !  = Network Byte Order (Big Endian) - Standard for networks
            #   I  = Unsigned Int (4 bytes) -> Magic Cookie
            #   B  = Unsigned Char (1 byte) -> Message Type
            #   H  = Unsigned Short (2 bytes) -> Server Port
            #   32s= String (32 bytes) -> Server Name
            cookie, msg_type, server_port, server_name_bytes = struct.unpack('!IBH32s', data[:39])

            # If the first 4 bytes aren't 0xabcddcba, this packet isn't from our game protocol.
            if cookie != MAGIC_COOKIE:
                return False

            # Offers must have type 0x2. If it's 0x3 or 0x4, it's the wrong packet type.
            if msg_type != MSG_TYPE_OFFER:
                return False

            # Save the port so we know where to connect via TCP later
            self.server_port = server_port

            # .decode('utf-8') turns bytes into a string.
            # .rstrip('\x00') removes the empty padding from the end
            server_name = server_name_bytes.decode('utf-8').rstrip('\x00').strip()

            print(f"Received valid offer from '{server_name}' at port {self.server_port}")
            return True

        except Exception as e:
            # If any error occurs (like unpacking failing), just ignore this packet.
            print(f"Error parsing offer: {e}")
            return False

    def connect_to_server(self):
        """
        Establishes TCP connection to the server and sends the request.
        """
        try:
            print(f"Connecting to server at {self.server_ip}:{self.server_port}...")

            # SOCK_STREAM = TCP protocol (reliable, connection-based)
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.tcp_socket.connect((self.server_ip, self.server_port))
            print(f"Connected successfully!")

            # 3. Ask User for Number of Rounds
            while True:
                try:
                    rounds_input = input("How many rounds do you want to play? ")
                    rounds = int(rounds_input)
                    if rounds > 0:
                        break
                    print("Please enter a positive number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            # 4. Pack the Request Message
            # [cite_start]Format according to [cite: 91-95]:
            # !    = Network Endian
            # I    = Magic Cookie (4 bytes)
            # B    = Message Type (1 byte) -> 0x3 for Request
            # B    = Number of Rounds (1 byte)
            # 32s  = Team Name (32 bytes)

            # Encode the team name and pad/truncate to 32 bytes handled by struct
            packet_data = struct.pack('!IBB32s',
                                      MAGIC_COOKIE,
                                      MSG_TYPE_REQUEST,
                                      rounds,
                                      self.player_name.encode('utf-8'))

            # 5. Send the data and line break
            self.tcp_socket.sendall(packet_data)
            self.tcp_socket.sendall(b'\n')

            print(f"Sent request to play {rounds} rounds.")
            self.play_game(rounds)


        except Exception as e:
            print(f"Error connecting to server: {e}")
            # Ensure socket is closed if connection fails
            if hasattr(self, 'tcp_socket'):
                self.tcp_socket.close()

    def play_game(self, rounds):
        """
        Handles the gameplay loop for the specified number of rounds.
        """
        print(f"--- Starting Game ({rounds} rounds) ---")

        RESULT_ACTIVE = 0x0
        RESULT_TIE = 0x1
        RESULT_LOSS = 0x2
        RESULT_WIN = 0x3
        rounds_played = 0
        wins = 0
        try:
            while rounds_played < rounds:
                print(f"\n--- Round {rounds_played + 1} ---")

                while True:
                    # 1. Wait for Server Payload (9 Bytes) : Cookie(4) + Type(1) + Result(1) + Card(3)
                    data = self.tcp_socket.recv(9)
                    if len(data) < 9:
                        print("Server disconnected or sent incomplete data.")
                        return

                    cookie, msg_type, result, card_val = struct.unpack('!IBB3s', data)

                    if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
                        print(f"Invalid packet received: {data}")
                        continue

                    # TODO: Parse the 'card_val' (3 bytes) to display a nice card name (e.g. "Ace of Spades")
                    print(f"Server sent card data: {card_val} | Game Status: {result}")

                    if result != RESULT_ACTIVE:
                        if result == RESULT_WIN:
                            print("Result: YOU WIN!")
                            wins += 1
                        elif result == RESULT_LOSS:
                            print("Result: YOU LOSE!")
                        elif result == RESULT_TIE:
                            print("Result: IT'S A TIE!")

                        rounds_played += 1
                        break

                    print("Your hand is still active.")
                    while True:
                        move = input("Action (h = Hit, s = Stand): ").lower()
                        if move in ['h', 's']:
                            break
                        print("Invalid input.")

                    # 4. Send Decision to Server (10 Bytes), Format: Cookie(4) + Type(1) + Decision(5)
                    decision_str = "Hittt" if move == 'h' else "Stand"

                    packet = struct.pack('!IB5s',
                                         MAGIC_COOKIE,
                                         MSG_TYPE_PAYLOAD,
                                         decision_str.encode('utf-8'))

                    self.tcp_socket.sendall(packet)
                    print(f"Sent decision: {decision_str}")

            print(f"\nFinished playing {rounds} rounds. Wins: {wins}")

        except Exception as e:
            print(f"Game error: {e}")
        finally:
            print("Closing connection...")
            if self.tcp_socket:
                self.tcp_socket.close()

    def start(self):
        """
        Main client loop.
        """
        while True:
            self.listen_for_offers()
            if self.server_ip and self.server_port:
                self.connect_to_server()

                # Reset for next game
                self.server_ip = None
                self.server_port = None


if __name__ == "__main__":
    client = Client()
    client.start()
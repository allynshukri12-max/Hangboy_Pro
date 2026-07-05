"""
================================================================================
                                HANGBOY PRO
            Authoritative Competitive Multiplayer Tournament Server
================================================================================
"""

from __future__ import annotations
import signal
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from network_utils import recv_msg, send_msg
import config

class Console:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    DIM = "\033[90m"
    BOLD = "\033[1m"

    @classmethod
    def event(cls, label: str, message: str = "", color: str = CYAN) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"{cls.DIM}{stamp}{cls.RESET} {color}{cls.BOLD}[{label}]{cls.RESET} {message}", flush=True)

def clean_value(value: object) -> str:
    return str(value).replace("|", "/").replace("\n", " ").replace("\r", " ").strip()

def make_packet(**fields: object) -> str:
    return "|".join(f"{key}:{clean_value(value)}" for key, value in fields.items())

def parse_packet(packet: str) -> Tuple[str, str]:
    if not packet or ":" not in packet:
        return packet.strip().upper(), ""
    command, value = packet.split(":", 1)
    return command.strip().upper(), value.strip()

@dataclass
class PlayerSession:
    name: str
    sock: socket.socket
    joined_at: float = field(default_factory=time.time)
    
    level_index: int = 0
    round_number: int = 1
    global_lives: int = config.STARTING_LIVES
    secret_word: str = ""
    hint: str = ""
    revealed_word: List[str] = field(default_factory=list)
    guessed_letters: Set[str] = field(default_factory=set)
    level_scores: List[int] = field(default_factory=lambda: [0] * config.LEVEL_COUNT)
    level_started_at: float = field(default_factory=time.time)
    
    finished_run: bool = False
    eliminated: bool = False
    ready_for_reset: bool = False

    total_guesses_count: int = 0
    correct_guesses_count: int = 0
    wrong_guesses_count: int = 0
    rounds_won_count: int = 0
    rounds_lost_count: int = 0

class HangboyServer:
    def __init__(self) -> None:
        self.host = config.SERVER_HOST
        self.port = config.SERVER_PORT
        self.server_socket: Optional[socket.socket] = None
        self.running = threading.Event()
        self.lock = threading.RLock()
        self.clients: Dict[socket.socket, PlayerSession] = {}
        
        self.tournament_active = False
        self.tournament_over = False
        self.winner_name = ""

    def start(self) -> None:
        signal.signal(signal.SIGINT, self._handle_shutdown)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.running.set()

        Console.event("SERVER STARTED", f"Listening on port {self.port}", Console.GREEN)
        threading.Thread(target=self._heartbeat_loop, daemon=True, name="Heartbeat").start()

        try:
            while self.running.is_set():
                try:
                    client_sock, address = self.server_socket.accept()
                except OSError:
                    break
                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, address),
                    daemon=True,
                    name=f"Client-{address[0]}:{address[1]}"
                ).start()
        finally:
            self.stop()

    def stop(self) -> None:
        if not self.running.is_set(): return
        self.running.clear()
        with self.lock:
            sockets = list(self.clients.keys())
            self.clients.clear()
        for s in sockets: self._close_socket(s)
        if self.server_socket:
            self._close_socket(self.server_socket)
            self.server_socket = None
        Console.event("SERVER STOPPED", "All active sockets closed down successfully.", Console.RED)

    def _handle_shutdown(self, _signum: int, _frame: object) -> None:
        self.stop()

    def _heartbeat_loop(self) -> None:
        while self.running.is_set():
            time.sleep(1)
            with self.lock:
                if self.clients:
                    if not self.tournament_active:
                        self._broadcast_lobby_snapshot()
                    else:
                        self._broadcast_snapshot_to_all("", "tick")

    def _handle_client(self, client_sock: socket.socket, address: Tuple[str, int]) -> None:
        player_name = ""
        try:
            join_packet = recv_msg(client_sock)
            command, nickname = parse_packet(join_packet or "")

            if command != "JOIN":
                send_msg(client_sock, make_packet(ERROR="INVALID_JOIN", MSG="First framework packet must be JOIN:name"))
                return

            player_name = "".join(c for c in nickname.upper().strip() if c.isalnum() or c in ("_", "-"))[:14]
            if not player_name:
                send_msg(client_sock, make_packet(ERROR="INVALID_NAME", MSG="Nickname structural parsing failure."))
                return

            with self.lock:
                if any(p.name == player_name for p in self.clients.values()):
                    send_msg(client_sock, make_packet(ERROR="DUPLICATE_NAME", MSG="Lobby nickname collision detected."))
                    return
                if self.tournament_active and not self.tournament_over:
                    self._broadcast_snapshot_to_all("", "tick")
                    send_msg(client_sock, make_packet(ERROR="LOCKED_MATCH", MSG="Lobby locked. Match in progress."))
                    return

                session = PlayerSession(name=player_name, sock=client_sock)
                self.clients[client_sock] = session
                self._load_player_puzzle_level(session)

            Console.event("JOINED", f"{player_name} bound from network node {address[0]}", Console.GREEN)
            self._broadcast_lobby_snapshot()

            with self.lock:
                if len(self.clients) >= config.REQUIRED_PLAYERS and not self.tournament_active:
                    self.tournament_active = True
                    Console.event("TOURNAMENT START", "All players released into active layers.", Console.MAGENTA)

            while self.running.is_set():
                packet = recv_msg(client_sock)
                if not packet: break
                self._process_client_payload(session, packet)

        except Exception as err:
            Console.event("PIPELINE FAULT", f"{player_name or 'Unknown'}: {err}", Console.RED)
        finally:
            self._evict_player(client_sock, player_name)

    def _evict_player(self, sock: socket.socket, name: str) -> None:
        with self.lock:
            self.clients.pop(sock, None)
        self._close_socket(sock)
        if name:
            Console.event("DISCONNECTED", name, Console.YELLOW)
            if not self.tournament_active:
                self._broadcast_lobby_snapshot()
            else:
                self._check_tournament_completion_gate()
                self._broadcast_snapshot_to_all(f"⚠ {name} abandoned the match instance.", "leave")

    def _load_player_puzzle_level(self, p: PlayerSession) -> None:
        level = config.WORDS_POOL[p.level_index]
        p.secret_word = level["word"].upper()
        p.hint = level["hint"]
        p.revealed_word = ["_" for _ in p.secret_word]
        p.guessed_letters.clear()
        p.global_lives = config.STARTING_LIVES
        p.level_started_at = time.time()

    def _process_client_payload(self, p: PlayerSession, packet: str) -> None:
        command, value = parse_packet(packet)
        with self.lock:
            if command == "GUESS" and self.tournament_active and not p.finished_run and not p.eliminated:
                self._process_guess(p, value)
            elif command == "REQUEST_NEXT":
                self._process_level_advancement(p)

    def _process_guess(self, p: PlayerSession, char: str) -> None:
        guess = char.strip().upper()[:1]
        if not guess.isalpha() or self.tournament_over: return
        if guess in p.guessed_letters or "_" not in p.revealed_word or p.global_lives <= 0: return

        p.total_guesses_count += 1
        p.guessed_letters.add(guess)
        
        if guess in p.secret_word:
            p.correct_guesses_count += 1
            hits = 0
            for i, letter in enumerate(p.secret_word):
                if letter == guess and p.revealed_word[i] == "_":
                    p.revealed_word[i] = guess
                    hits += 1
            p.level_scores[p.level_index] += config.POINT_PER_LETTER * hits
            msg = f"✓ {p.name} matched character '{guess}' successfully."
            evt = "correct"

            if "_" not in p.revealed_word:
                p.rounds_won_count += 1
                p.level_scores[p.level_index] += config.LEVEL_BONUS
                if p.level_index + 1 >= config.LEVEL_COUNT:
                    p.finished_run = True
                    msg = f"🎉 {p.name} finished all levels perfectly!"
                    evt = "player_finished"
                    self._check_tournament_completion_gate()
                else:
                    msg = f"🏆 {p.name} cleared level {p.level_index + 1}!"
                    evt = "level_clear"
        else:
            p.wrong_guesses_count += 1
            p.global_lives -= 1
            msg = f"✗ {p.name} structural guess miss on '{guess}'."
            evt = "wrong"

            if p.global_lives <= 0:
                p.rounds_lost_count += 1
                p.eliminated = True
                msg = f"⚠ {p.name} lost this round. Word was: {p.secret_word}."
                evt = "player_dead"
                self._check_tournament_completion_gate()

        Console.event("GAME PIPELINE EVENT", msg, Console.CYAN)
        self._broadcast_snapshot_to_all(msg, evt)

    def _process_level_advancement(self, p: PlayerSession) -> None:
        if self.tournament_over:
            p.ready_for_reset = True
            if all(session.ready_for_reset for session in self.clients.values()):
                self.tournament_active = False
                self.tournament_over = False
                self.winner_name = ""
                for session in self.clients.values():
                    session.level_index = 0
                    session.round_number = 1
                    session.eliminated = False
                    session.finished_run = False
                    session.ready_for_reset = False
                    session.level_scores = [0] * config.LEVEL_COUNT
                    session.total_guesses_count = 0
                    session.correct_guesses_count = 0
                    session.wrong_guesses_count = 0
                    session.rounds_won_count = 0
                    session.rounds_lost_count = 0
                    self._load_player_puzzle_level(session)
                Console.event("TOURNAMENT RESET", "Reverted layout completely to lobby.", Console.GREEN)
                self._broadcast_lobby_snapshot()
            return

        if p.finished_run or p.eliminated: return

        if "_" not in p.revealed_word and p.level_index + 1 < config.LEVEL_COUNT:
            p.level_index += 1
            p.round_number += 1
            self._load_player_puzzle_level(p)
            self._broadcast_snapshot_to_all(f"🏆 {p.name} advanced to Level {p.level_index + 1}.", "level_up")

    def _check_tournament_completion_gate(self) -> None:
        if not self.clients: return
        all_done = all((p.finished_run or p.eliminated) for p in self.clients.values())
        if all_done and not self.tournament_over:
            self.tournament_over = True

            leaderboard = self._get_compiled_rankings()

            top_score = leaderboard[0][1]

            leaders = [
                row
                for row in leaderboard
                if row[1] == top_score
            ]

            if len(leaders) == 1:
                self.winner_name = leaders[0][0]
            else:
                self.winner_name = leaders[0][0]

            Console.event(
                "TOURNAMENT CONCLUDED",
                f"Crowned Winner: {self.winner_name}",
                Console.MAGENTA
            )

            # <-- INSIDE the if block
            self._broadcast_snapshot_to_all(
                "Tournament Finished!",
                "gameover"
            )

    def _get_compiled_rankings(self):
        board = []

        for p in self.clients.values():

            total = sum(p.level_scores)

            accuracy = (
                p.correct_guesses_count / p.total_guesses_count
                if p.total_guesses_count
                else 1.0
            )

            board.append((
                p.name,
                total,
                p.level_scores,
                p.rounds_won_count,
                p.wrong_guesses_count,
                accuracy
            ))

        board.sort(
            key=lambda x: (
                -x[1],      # score
                -x[3],      # rounds won
                x[4],       # fewer wrong guesses
                -x[5],      # accuracy
                x[0]        # alphabetical
            )
        )

        return [(n,s,l) for n,s,l,*_ in board]

    def _broadcast_lobby_snapshot(self) -> None:
        all_players = ",".join(p.name for p in self.clients.values()) or "None"
        count = len(self.clients)
        status_txt = f"Waiting for Players ({count}/{config.REQUIRED_PLAYERS})..." if count < config.REQUIRED_PLAYERS else "Match Starting..."
        packet = make_packet(
            PHASE="LOBBY",
            PLAYERS=all_players,
            STATUS=status_txt,
            READY_COUNT=f"{count}/{config.REQUIRED_PLAYERS}"
        )
        for s in list(self.clients.keys()): send_msg(s, packet)

    def _broadcast_snapshot_to_all(self, activity_msg: str, global_evt: str) -> None:
        with self.lock:
            leaderboard = self._get_compiled_rankings()
            leaderboard_str = ";".join(
                f"{rank},{name},{scores[0]},{scores[1]},{scores[2]},{scores[3]},{scores[4]},{total}"
                for rank, (name, total, scores) in enumerate(leaderboard, start=1)
            )
            all_players = ",".join(p.name for p in self.clients.values()) or "None"
            
            total_players = len(self.clients)
            finished_count = sum(1 for p in self.clients.values() if p.finished_run or p.eliminated)
            remaining_count = total_players - finished_count
            final_ranks_map = {name: rank for rank, (name, _, _) in enumerate(leaderboard, start=1)}

            for s in list(self.clients.keys()):
                p = self.clients[s]
                elapsed = int(time.time() - p.level_started_at)
                accuracy = 100.0 if p.total_guesses_count == 0 else (p.correct_guesses_count / p.total_guesses_count) * 100.0
                my_rank = final_ranks_map.get(p.name, 1)
                champion_score = leaderboard[0][1] if leaderboard else 0

                my_sub_phase = "PLAYING"
                if p.finished_run: my_sub_phase = "WAITING_COMPLETED"
                if p.eliminated: my_sub_phase = "WAITING_DEFEATED"

                packet = make_packet(
                    PHASE="TOURNAMENT",
                    SUBPHASE=my_sub_phase,
                    WORD=" ".join(p.revealed_word),
                    HINT=p.hint,
                    SECRET=p.secret_word,
                    LIVES=p.global_lives,
                    MAX_LIVES=config.STARTING_LIVES,
                    LEVEL=p.level_index + 1,
                    ROUND=p.round_number,
                    TIMER=f"{elapsed // 60:02d}:{elapsed % 60:02d}",
                    PLAYERS=all_players,
                    LIVE_LEADERBOARD=leaderboard_str,
                    RANKINGS=leaderboard_str,
                    MSG=activity_msg,
                    EVENT=global_evt,
                    GAMEOVER="YES" if self.tournament_over else "NO",
                    WINNER=self.winner_name,
                    
                    MY_RANK=my_rank,
                    MY_SCORE=sum(p.level_scores),
                    CHAMPION_SCORE=champion_score,
                    ACCURACY=f"{accuracy:.1f}%",
                    CORRECT_GUESSES=p.correct_guesses_count,
                    WRONG_GUESSES=p.wrong_guesses_count,
                    ROUNDS_WON=p.rounds_won_count,
                    ROUNDS_LOST=p.rounds_lost_count,
                    
                    FINISHED_COUNT=finished_count,
                    REMAINING_COUNT=remaining_count,
                    TOTAL_PLAYERS=total_players
                )
                send_msg(s, packet)

    def _close_socket(self, sock: socket.socket) -> None:
        try: sock.shutdown(socket.SHUT_RDWR)
        except OSError: pass
        try: sock.close()
        except OSError: pass

if __name__ == "__main__":
    try: HangboyServer().start()
    except KeyboardInterrupt: pass
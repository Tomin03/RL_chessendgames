import gymnasium as gym
from gymnasium import spaces
import chess
import random
import json
import numpy as np


class ChessEnv(gym.Env):
    def __init__(self, positions_file="positions.json", max_steps=100):
        super().__init__()

        with open(positions_file, "r") as f:
            self.positions = json.load(f)

        self.action_space = spaces.Discrete(218)

        # +1 kanał na "side to move"
        self.observation_space = spaces.Box(
            low=0,
            high=1,
            shape=(8, 8, 13),
            dtype=np.float32
        )

        self.max_steps = max_steps
        self.current_step = 0

    # =========================
    # RESET
    # =========================
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        fen = random.choice(self.positions)
        self.board = chess.Board(fen)

        self.current_step = 0

        return self._get_obs(), {}

    # =========================
    # STEP (SELF-PLAY)
    # =========================
    def step(self, action):
        self.current_step += 1

        legal_moves = list(self.board.legal_moves)

        if len(legal_moves) == 0:
            return self._get_obs(), 0, True, False, {}

        if action >= len(legal_moves):
            action = random.randint(0, len(legal_moves) - 1)

        move = legal_moves[action]

        reward = 0

        # -------------------------
        # REWARD: capture
        # -------------------------
        if self.board.is_capture(move):
            reward += 0.2

        # -------------------------
        # wykonaj ruch
        # -------------------------
        self.board.push(move)

        # kara za długość gry
        reward -= 0.01

        done = self.board.is_game_over()
        truncated = False

        # -------------------------
        # REWARD: wynik gry (SELF-PLAY!)
        # -------------------------
        if done:
            result = self.board.result()

            # UWAGA: po wykonaniu ruchu zmienia się turn!
            # więc patrzymy kto NIE ma ruchu = kto wygrał
            if result == "1-0":
                reward = 1 if self.board.turn == chess.BLACK else -1
            elif result == "0-1":
                reward = 1 if self.board.turn == chess.WHITE else -1
            else:
                reward = 0

        # limit długości
        if self.current_step >= self.max_steps:
            truncated = True

        return self._get_obs(), reward, done, truncated, {}

    # =========================
    # OBSERVATION (SELF-PLAY!)
    # =========================
    def _get_obs(self):
        board = self.board

        # 🔥 KLUCZOWE: mirror → zawsze perspektywa gracza na ruchu
        if not board.turn:
            board = board.mirror()

        board_array = np.zeros((8, 8, 12), dtype=np.float32)

        for square, piece in board.piece_map().items():
            row = square // 8
            col = square % 8

            piece_type = piece.piece_type - 1
            color_offset = 0 if piece.color else 6

            channel = piece_type + color_offset
            board_array[row][col][channel] = 1

        # kanał: side to move (po mirrorze zawsze 1)
        turn_plane = np.ones((8, 8, 1), dtype=np.float32)

        return np.concatenate([board_array, turn_plane], axis=2)

    # =========================
    # ACTION MASKING
    # =========================
    def action_masks(self):
        mask = np.zeros(218, dtype=np.int8)

        legal_moves = list(self.board.legal_moves)

        for i in range(len(legal_moves)):
            mask[i] = 1

        return mask
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

        # maksymalna liczba ruchów (bezpieczny limit)
        self.action_space = spaces.Discrete(218)

        # plansza 8x8x12 (6 figur * 2 kolory)
        self.observation_space = spaces.Box(
            low=0,
            high=1,
            shape=(8, 8, 12),
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
    # STEP
    # =========================
    def step(self, action):
        self.current_step += 1

        legal_moves = list(self.board.legal_moves)

        # zabezpieczenie
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

        # -------------------------
        # kara za długość gry
        # -------------------------
        reward -= 0.01

        done = self.board.is_game_over()
        truncated = False

        # -------------------------
        # REWARD: wynik gry
        # -------------------------
        if done:
            result = self.board.result()

            if result == "1-0":
                reward = 1
            elif result == "0-1":
                reward = -1
            else:
                reward = 0

        # -------------------------
        # limit długości epizodu
        # -------------------------
        if self.current_step >= self.max_steps:
            truncated = True

        return self._get_obs(), reward, done, truncated, {}

    # =========================
    # OBSERVATION (tensor)
    # =========================
    def _get_obs(self):
        board_array = np.zeros((8, 8, 12), dtype=np.float32)

        for square, piece in self.board.piece_map().items():
            row = square // 8
            col = square % 8

            piece_type = piece.piece_type - 1
            color_offset = 0 if piece.color else 6

            channel = piece_type + color_offset

            board_array[row][col][channel] = 1

        return board_array

    # =========================
    # ACTION MASKING
    # =========================
    def action_masks(self):
        mask = np.zeros(218, dtype=np.int8)

        legal_moves = list(self.board.legal_moves)

        for i in range(len(legal_moves)):
            mask[i] = 1

        return mask
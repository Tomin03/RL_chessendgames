import json
import random
from pathlib import Path

import chess
import gymnasium as gym
import numpy as np
from gymnasium import spaces


class ChessEnv(gym.Env):
    def __init__(self, positions_file="positions.json", max_steps=100):
        super().__init__()

        positions_path = Path(positions_file)
        if not positions_path.is_absolute():
            positions_path = Path(__file__).resolve().parent / positions_path

        with positions_path.open("r", encoding="utf-8") as f:
            self.positions = json.load(f)

        self.action_space = spaces.Discrete(218)
        self.observation_space = spaces.Box(
            low=0,
            high=1,
            shape=(8, 8, 13),
            dtype=np.float32,
        )

        self.max_steps = max_steps
        self.current_step = 0
        self.board = chess.Board()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.board = chess.Board(random.choice(self.positions))
        self.current_step = 0
        return self._get_obs(), {}

    def step(self, action):
        self.current_step += 1
        legal_moves = list(self.board.legal_moves)

        if not legal_moves:
            return self._get_obs(), 0, True, False, {}

        action = int(action)
        if action >= len(legal_moves):
            move = random.choice(legal_moves)
            reward = -0.1
        else:
            move = legal_moves[action]
            reward = 0

        if self.board.is_capture(move):
            reward += 0.2

        self.board.push(move)
        reward -= 0.01

        done = self.board.is_game_over()
        truncated = self.current_step >= self.max_steps

        if done:
            result = self.board.result()
            if result == "1-0":
                reward = 1 if self.board.turn == chess.BLACK else -1
            elif result == "0-1":
                reward = 1 if self.board.turn == chess.WHITE else -1
            else:
                reward = 0

        return self._get_obs(), reward, done, truncated, {}

    def _get_obs(self):
        board = self.board.copy()
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

        turn_plane = np.ones((8, 8, 1), dtype=np.float32)
        return np.concatenate([board_array, turn_plane], axis=2)

    def action_masks(self):
        mask = np.zeros(self.action_space.n, dtype=np.int8)
        legal_moves_count = min(len(list(self.board.legal_moves)), self.action_space.n)
        mask[:legal_moves_count] = 1
        return mask

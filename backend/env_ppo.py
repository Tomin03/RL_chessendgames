import json
import random
from pathlib import Path

import chess
import gymnasium as gym
import numpy as np
from gymnasium import spaces


PIECE_VALUES = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.0,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
    chess.KING: 0.0,
}


def generate_action_space():
    actions = []
    promotion_pieces = ["q", "r", "b", "n"]

    for from_square in chess.SQUARES:
        for to_square in chess.SQUARES:
            if from_square == to_square:
                continue

            move = chess.Move(from_square, to_square)
            actions.append(move.uci())

            from_rank = chess.square_rank(from_square)
            to_rank = chess.square_rank(to_square)
            is_promotion_rank = (from_rank == 6 and to_rank == 7) or (from_rank == 1 and to_rank == 0)
            if is_promotion_rank:
                for promotion in promotion_pieces:
                    actions.append(f"{move.uci()}{promotion}")

    return actions


ALL_ACTIONS = generate_action_space()
ACTION_TO_INDEX = {uci: index for index, uci in enumerate(ALL_ACTIONS)}
ACTION_SPACE_SIZE = len(ALL_ACTIONS)


def move_to_action_index(move: chess.Move):
    return ACTION_TO_INDEX.get(move.uci())


def action_index_to_move(action: int):
    if 0 <= action < ACTION_SPACE_SIZE:
        return chess.Move.from_uci(ALL_ACTIONS[action])
    return None


def material_score(board: chess.Board, color: chess.Color):
    score = 0.0
    for piece in board.piece_map().values():
        value = PIECE_VALUES[piece.piece_type]
        score += value if piece.color == color else -value
    return score


def king_activity_score(board: chess.Board, color: chess.Color):
    king_square = board.king(color)
    if king_square is None:
        return 0.0

    file_distance = abs(chess.square_file(king_square) - 3.5)
    rank_distance = abs(chess.square_rank(king_square) - 3.5)
    return (7 - file_distance - rank_distance) / 7


def is_passed_pawn(board: chess.Board, square: chess.Square, color: chess.Color):
    file_index = chess.square_file(square)
    rank_index = chess.square_rank(square)
    enemy_pawns = board.pieces(chess.PAWN, not color)

    for enemy_square in enemy_pawns:
        enemy_file = chess.square_file(enemy_square)
        enemy_rank = chess.square_rank(enemy_square)
        if abs(enemy_file - file_index) > 1:
            continue

        if color == chess.WHITE and enemy_rank > rank_index:
            return False
        if color == chess.BLACK and enemy_rank < rank_index:
            return False

    return True


def pawn_progress_score(board: chess.Board, color: chess.Color):
    score = 0.0
    for square, piece in board.piece_map().items():
        if piece.piece_type != chess.PAWN or piece.color != color:
            continue

        rank = chess.square_rank(square)
        progress = rank if color == chess.WHITE else 7 - rank
        score += progress / 6

        if is_passed_pawn(board, square, color):
            score += 0.6 + progress / 6

    return score


def heuristic_score(board: chess.Board, color: chess.Color):
    opponent = not color
    return (
        material_score(board, color)
        + 0.35 * (pawn_progress_score(board, color) - pawn_progress_score(board, opponent))
        + 0.2 * (king_activity_score(board, color) - king_activity_score(board, opponent))
    )


class ChessEnv(gym.Env):
    def __init__(self, positions_file="positions.json", max_steps=100):
        super().__init__()

        positions_path = Path(positions_file)
        if not positions_path.is_absolute():
            positions_path = Path(__file__).resolve().parent / positions_path

        with positions_path.open("r", encoding="utf-8") as f:
            self.positions = json.load(f)

        self.action_space = spaces.Discrete(ACTION_SPACE_SIZE)
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
        move = action_index_to_move(action)
        if move not in legal_moves:
            move = random.choice(legal_moves)
            reward = -0.5
        else:
            reward = 0.0

        moving_color = self.board.turn
        score_before = heuristic_score(self.board, moving_color)

        if self.board.is_capture(move):
            captured_piece = self.board.piece_at(move.to_square)
            if captured_piece:
                reward += 0.1 * PIECE_VALUES[captured_piece.piece_type]

        if move.promotion:
            reward += 1.5

        self.board.push(move)
        score_after = heuristic_score(self.board, moving_color)

        reward += 0.08 * (score_after - score_before)
        if self.board.is_check():
            reward += 0.05
        reward -= 0.01

        done = self.board.is_game_over()
        truncated = self.current_step >= self.max_steps

        if done:
            result = self.board.result()
            if result == "1-0":
                reward += 10 if moving_color == chess.WHITE else -10
            elif result == "0-1":
                reward += 10 if moving_color == chess.BLACK else -10
            elif material_score(self.board, moving_color) > 1:
                reward -= 2

        return self._get_obs(), reward, done, truncated, {}

    def _get_obs(self):
        board_array = np.zeros((8, 8, 12), dtype=np.float32)
        for square, piece in self.board.piece_map().items():
            row = square // 8
            col = square % 8
            piece_type = piece.piece_type - 1
            color_offset = 0 if piece.color else 6
            channel = piece_type + color_offset
            board_array[row][col][channel] = 1

        turn_value = 1.0 if self.board.turn == chess.WHITE else 0.0
        turn_plane = np.full((8, 8, 1), turn_value, dtype=np.float32)
        return np.concatenate([board_array, turn_plane], axis=2)

    def action_masks(self):
        mask = np.zeros(self.action_space.n, dtype=np.int8)
        for move in self.board.legal_moves:
            action_index = move_to_action_index(move)
            if action_index is not None:
                mask[action_index] = 1
        return mask

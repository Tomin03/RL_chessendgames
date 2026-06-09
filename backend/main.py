from pathlib import Path
import json
import random

import chess
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sb3_contrib import MaskablePPO
from torch.distributions import Distribution

from backend.env_ppo import (
    ACTION_SPACE_SIZE,
    action_index_to_move,
    heuristic_score,
    move_to_action_index,
)

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "ppo_chess_model_tuned.zip"
POSITIONS_PATH = BASE_DIR / "positions.json"

Distribution.set_default_validate_args(False)

model = MaskablePPO.load(str(MODEL_PATH))

with POSITIONS_PATH.open("r", encoding="utf-8") as f:
    positions_catalog = json.load(f)

positions = [
    position["fen"] if isinstance(position, dict) else position
    for position in positions_catalog
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def board_to_obs(board: chess.Board):
    board_array = np.zeros((8, 8, 12), dtype=np.float32)

    for square, piece in board.piece_map().items():
        row = square // 8
        col = square % 8
        piece_type = piece.piece_type - 1
        color_offset = 0 if piece.color else 6
        channel = piece_type + color_offset
        board_array[row][col][channel] = 1

    turn_value = 1.0 if board.turn == chess.WHITE else 0.0
    turn_plane = np.full((8, 8, 1), turn_value, dtype=np.float32)

    return np.concatenate([board_array, turn_plane], axis=2)


def is_playable_position(fen: str) -> bool:
    try:
        board = chess.Board(fen)
    except ValueError:
        return False

    if not board.is_valid() or board.is_game_over():
        return False

    pieces = board.piece_map().values()
    white_kings = sum(
        1
        for piece in pieces
        if piece.piece_type == chess.KING and piece.color == chess.WHITE
    )
    black_kings = sum(
        1
        for piece in pieces
        if piece.piece_type == chess.KING and piece.color == chess.BLACK
    )

    return white_kings == 1 and black_kings == 1 and any(board.legal_moves)


def position_payload(fen: str):
    board = chess.Board(fen)
    turn = "white" if board.turn == chess.WHITE else "black"

    return {
        "fen": board.fen(),
        "turn": turn,
        "playerColor": turn,
        "gameOver": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
    }


def catalog_payload(position, index: int):
    fen = position["fen"] if isinstance(position, dict) else position
    fallback_name = f"Pozycja {index + 1}"

    return {
        "id": position.get("id", str(index)) if isinstance(position, dict) else str(index),
        "name": position.get("name", fallback_name) if isinstance(position, dict) else fallback_name,
        "description": position.get("description", "") if isinstance(position, dict) else "",
        **position_payload(fen),
    }


def legal_action_masks(board: chess.Board):
    legal_moves = list(board.legal_moves)
    action_count = model.action_space.n
    action_masks = np.zeros(action_count, dtype=bool)

    if action_count == ACTION_SPACE_SIZE:
        for legal_move in legal_moves:
            action_idx = move_to_action_index(legal_move)
            if action_idx is not None and 0 <= action_idx < action_count:
                action_masks[action_idx] = True
    else:
        for action_idx in range(min(len(legal_moves), action_count)):
            action_masks[action_idx] = True

    return legal_moves, action_masks


def fallback_move_score(board: chess.Board, move: chess.Move, moving_color: chess.Color):
    board_copy = board.copy(stack=False)
    before = heuristic_score(board_copy, moving_color)
    board_copy.push(move)

    if board_copy.is_checkmate():
        return 1000.0
    if board_copy.is_game_over():
        return 0.0

    return heuristic_score(board_copy, moving_color) - before


def move_ranking_for_board(board: chess.Board, limit: int = 8):
    legal_moves, action_masks = legal_action_masks(board)
    if not legal_moves:
        return []

    action_count = model.action_space.n
    moving_color = board.turn
    probabilities = None

    try:
        obs_tensor, _ = model.policy.obs_to_tensor(board_to_obs(board))
        distribution = model.policy.get_distribution(
            obs_tensor,
            action_masks=action_masks.reshape(1, -1),
        )
        probabilities = distribution.distribution.probs.detach().cpu().numpy()[0]
    except Exception as exc:
        print("\n=== MOVE RANKING POLICY ERROR ===")
        print(exc)

    ranked_moves = []
    for move in legal_moves:
        action_idx = move_to_action_index(move)
        probability = None

        if probabilities is not None and action_idx is not None and 0 <= action_idx < action_count:
            score = float(probabilities[action_idx])
            probability = score
        else:
            score = fallback_move_score(board, move, moving_color)

        ranked_moves.append(
            {
                "move": move.uci(),
                "san": board.san(move),
                "score": score,
                "probability": probability,
            }
        )

    ranked_moves.sort(key=lambda item: item["score"], reverse=True)

    for index, item in enumerate(ranked_moves, start=1):
        item["rank"] = index

    return ranked_moves[:limit]


def choose_agent_move(board: chess.Board):
    legal_moves, action_masks = legal_action_masks(board)

    if not legal_moves:
        return None, action_masks

    valid_actions = int(np.sum(action_masks))
    if valid_actions == 0:
        print("\n=== ZERO VALID ACTIONS ===")
        print("FEN:", board.fen())
        print("Legal moves:", [move.uci() for move in legal_moves])
        return random.choice(legal_moves), action_masks

    try:
        action, _ = model.predict(
            board_to_obs(board),
            action_masks=action_masks,
            deterministic=True,
        )
        action = int(action)
    except Exception as exc:
        print("\n=== MODEL PREDICT ERROR ===")
        print(exc)
        print("FEN:", board.fen())
        print("Legal moves:", [move.uci() for move in legal_moves])
        return random.choice(legal_moves), action_masks

    if model.action_space.n == ACTION_SPACE_SIZE:
        move = action_index_to_move(action)
        if move not in legal_moves:
            print("\n=== INVALID MODEL MOVE ===")
            print("Predicted:", move)
            print("Legal:", [legal_move.uci() for legal_move in legal_moves])
            move = random.choice(legal_moves)
    else:
        if action >= len(legal_moves):
            action = random.randint(0, len(legal_moves) - 1)
        move = legal_moves[action]

    if move not in legal_moves:
        move = random.choice(legal_moves)

    return move, action_masks


@app.get("/")
def home():
    return {"message": "PPO Chess Backend Running"}


@app.get("/positions")
def list_positions():
    return [
        catalog_payload(position, index)
        for index, position in enumerate(positions_catalog)
        if is_playable_position(position["fen"] if isinstance(position, dict) else position)
    ]


@app.get("/random_position")
def random_position():
    valid_positions = [fen for fen in positions if is_playable_position(fen)]

    if not valid_positions:
        return position_payload("8/8/8/3k4/8/4K3/3P4/8 w - - 0 1")

    return position_payload(random.choice(valid_positions))


@app.post("/ai_move")
def ai_move(data: dict):
    fen = data.get("fen")

    if not fen:
        raise HTTPException(status_code=400, detail="Missing fen")

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid fen") from exc

    if board.is_game_over():
        return {
            "move": None,
            "fen": board.fen(),
            "gameOver": True,
            "result": board.result(),
        }

    move, _ = choose_agent_move(board)
    if move is None:
        return {
            "move": None,
            "fen": board.fen(),
            "gameOver": True,
            "result": board.result() if board.is_game_over() else None,
        }

    board.push(move)

    return {
        "move": move.uci(),
        "fen": board.fen(),
        "gameOver": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
    }


@app.post("/move_ranking")
def move_ranking(data: dict):
    fen = data.get("fen")
    limit = int(data.get("limit", 8))

    if not fen:
        raise HTTPException(status_code=400, detail="Missing fen")

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid fen") from exc

    return {
        "fen": board.fen(),
        "moves": move_ranking_for_board(board, limit=max(1, min(limit, 20))),
    }

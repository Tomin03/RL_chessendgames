from pathlib import Path
import json
import random

import chess
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sb3_contrib import MaskablePPO

from backend.env_ppo import (
    ACTION_SPACE_SIZE,
    action_index_to_move,
    move_to_action_index,
)

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "ppo_chess_model.zip"
POSITIONS_PATH = BASE_DIR / "positions.json"

model = MaskablePPO.load(str(MODEL_PATH))

with POSITIONS_PATH.open("r", encoding="utf-8") as f:
    positions = json.load(f)

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

    return (
        white_kings == 1
        and black_kings == 1
        and any(board.legal_moves)
    )


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


@app.get("/")
def home():
    return {"message": "PPO Chess Backend Running"}


@app.get("/random_position")
def random_position():
    valid_positions = [
        fen for fen in positions if is_playable_position(fen)
    ]

    if not valid_positions:
        return position_payload(
            "8/8/8/3k4/8/4K3/3P4/8 w - - 0 1"
        )

    return position_payload(random.choice(valid_positions))


@app.post("/ai_move")
def ai_move(data: dict):
    fen = data.get("fen")

    if not fen:
        raise HTTPException(
            status_code=400,
            detail="Missing fen",
        )

    try:
        board = chess.Board(fen)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid fen",
        ) from exc

    if board.is_game_over():
        return {
            "move": None,
            "fen": board.fen(),
            "gameOver": True,
            "result": board.result(),
        }

    legal_moves = list(board.legal_moves)

    if len(legal_moves) == 0:
        return {
            "move": None,
            "fen": board.fen(),
            "gameOver": True,
            "result": board.result(),
        }

    action_count = model.action_space.n

    # WAŻNE: bool zamiast int8
    action_masks = np.zeros(action_count, dtype=bool)

    # Mapowanie legalnych ruchów
    if action_count == ACTION_SPACE_SIZE:

        for legal_move in legal_moves:

            action_idx = move_to_action_index(legal_move)

            if action_idx is not None:

                if 0 <= action_idx < action_count:
                    action_masks[action_idx] = True

    else:

        for action_idx in range(
            min(len(legal_moves), action_count)
        ):
            action_masks[action_idx] = True

    # DEBUG
    valid_actions = int(np.sum(action_masks))

    if valid_actions == 0:

        print("\n=== ZERO VALID ACTIONS ===")
        print("FEN:", board.fen())

        print(
            "Legal moves:",
            [m.uci() for m in legal_moves],
        )

        fallback_move = random.choice(legal_moves)

        board.push(fallback_move)

        return {
            "move": fallback_move.uci(),
            "fen": board.fen(),
            "gameOver": board.is_game_over(),
            "result": (
                board.result()
                if board.is_game_over()
                else None
            ),
        }

    try:

        action, _ = model.predict(
            board_to_obs(board),
            action_masks=action_masks,
            deterministic=True,
        )

        action = int(action)

    except Exception as e:

        print("\n=== MODEL PREDICT ERROR ===")
        print(e)

        print("FEN:", board.fen())

        print(
            "Legal moves:",
            [m.uci() for m in legal_moves],
        )

        fallback_move = random.choice(legal_moves)

        board.push(fallback_move)

        return {
            "move": fallback_move.uci(),
            "fen": board.fen(),
            "gameOver": board.is_game_over(),
            "result": (
                board.result()
                if board.is_game_over()
                else None
            ),
        }

    # Zamiana akcji na ruch
    if action_count == ACTION_SPACE_SIZE:

        move = action_index_to_move(action)

        # Zabezpieczenie
        if move not in legal_moves:

            print("\n=== INVALID MODEL MOVE ===")
            print("Predicted:", move)

            print(
                "Legal:",
                [m.uci() for m in legal_moves],
            )

            move = random.choice(legal_moves)

    else:

        if action >= len(legal_moves):
            action = random.randint(
                0,
                len(legal_moves) - 1,
            )

        move = legal_moves[action]

    # Finalne zabezpieczenie
    if move not in legal_moves:
        move = random.choice(legal_moves)

    board.push(move)

    return {
        "move": move.uci(),
        "fen": board.fen(),
        "gameOver": board.is_game_over(),
        "result": (
            board.result()
            if board.is_game_over()
            else None
        ),
    }
from pathlib import Path
import json
import random

import chess
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sb3_contrib import MaskablePPO


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
    temp_board = board.copy()
    if not temp_board.turn:
        temp_board = temp_board.mirror()

    board_array = np.zeros((8, 8, 12), dtype=np.float32)
    for square, piece in temp_board.piece_map().items():
        row = square // 8
        col = square % 8
        piece_type = piece.piece_type - 1
        color_offset = 0 if piece.color else 6
        channel = piece_type + color_offset
        board_array[row][col][channel] = 1

    turn_plane = np.ones((8, 8, 1), dtype=np.float32)
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


@app.get("/")
def home():
    return {"message": "PPO Chess Backend Running"}


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

    legal_moves = list(board.legal_moves)
    action_count = model.action_space.n
    action_masks = np.zeros(action_count, dtype=np.int8)

    for action_idx in range(min(len(legal_moves), action_count)):
        action_masks[action_idx] = 1

    action, _ = model.predict(
        board_to_obs(board),
        action_masks=action_masks,
        deterministic=True,
    )

    action = int(action)
    if action >= len(legal_moves):
        action = random.randint(0, len(legal_moves) - 1)

    move = legal_moves[action]

    board.push(move)
    return {
        "move": move.uci(),
        "fen": board.fen(),
        "gameOver": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
    }

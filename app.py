import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import chess
import json
import random
import numpy as np

from sb3_contrib import MaskablePPO

# =====================================================
# CONFIG
# =====================================================

MODEL_PATH = "ppo_chess_model"
POSITIONS_FILE = "positions.json"

BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8

HUMAN_COLOR = chess.WHITE
AI_COLOR = chess.BLACK

# =====================================================
# LOAD MODEL
# =====================================================

print("Ładowanie modelu PPO...")
model = MaskablePPO.load(MODEL_PATH)

# =====================================================
# LOAD POSITIONS
# =====================================================

with open(POSITIONS_FILE, "r") as f:
    positions = json.load(f)

# =====================================================
# START POSITION
# =====================================================

while True:

    fen = random.choice(positions)
    temp_board = chess.Board(fen)

    if temp_board.turn == HUMAN_COLOR:
        board = temp_board
        break

# =====================================================
# OBSERVATION
# =====================================================

def board_to_obs(board):

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

# =====================================================
# AI MOVE
# =====================================================

def ai_move():

    global board

    if board.turn != AI_COLOR:
        return

    legal_moves = list(board.legal_moves)

    if len(legal_moves) == 0:
        return

    obs = board_to_obs(board)

    action_masks = np.zeros(218, dtype=np.int8)

    for i in range(len(legal_moves)):
        action_masks[i] = 1

    action, _ = model.predict(
        obs,
        action_masks=action_masks,
        deterministic=True
    )

    if action >= len(legal_moves):
        action = random.randint(0, len(legal_moves) - 1)

    move = legal_moves[action]

    print("AI move:", move)

    board.push(move)

# =====================================================
# TKINTER
# =====================================================

root = tk.Tk()
root.title("♟ PPO Chess Endgame Agent")

canvas = tk.Canvas(root, width=BOARD_SIZE, height=BOARD_SIZE)
canvas.pack()

selected_square = None

# =====================================================
# LOAD PIECES
# =====================================================

piece_images = {}

piece_names = {
    "P": "wp",
    "N": "wn",
    "B": "wb",
    "R": "wr",
    "Q": "wq",
    "K": "wk",
    "p": "bp",
    "n": "bn",
    "b": "bb",
    "r": "br",
    "q": "bq",
    "k": "bk",
}

for piece_symbol, filename in piece_names.items():

    img = Image.open(f"pieces/{filename}.png")
    img = img.resize((SQUARE_SIZE, SQUARE_SIZE))

    piece_images[piece_symbol] = ImageTk.PhotoImage(img)

# =====================================================
# DRAW BOARD
# =====================================================

def draw_board():

    canvas.delete("all")

    colors = ["#F0D9B5", "#B58863"]

    for rank in range(8):

        for file in range(8):

            x1 = file * SQUARE_SIZE
            y1 = (7 - rank) * SQUARE_SIZE

            x2 = x1 + SQUARE_SIZE
            y2 = y1 + SQUARE_SIZE

            color = colors[(rank + file) % 2]

            canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline=color
            )

            square = chess.square(file, rank)

            piece = board.piece_at(square)

            if piece:

                canvas.create_image(
                    x1,
                    y1,
                    anchor=tk.NW,
                    image=piece_images[piece.symbol()]
                )

# =====================================================
# CLICK HANDLER
# =====================================================

def on_click(event):

    global selected_square
    global board

    if board.is_game_over():
        return

    if board.turn != HUMAN_COLOR:
        return

    file = event.x // SQUARE_SIZE
    rank = 7 - (event.y // SQUARE_SIZE)

    clicked_square = chess.square(file, rank)

    piece = board.piece_at(clicked_square)

    # SELECT PIECE
    if selected_square is None:

        if piece and piece.color == HUMAN_COLOR:
            selected_square = clicked_square

        return

    # TRY MOVE
    move = chess.Move(selected_square, clicked_square)

    moving_piece = board.piece_at(selected_square)

    # promotion
    if moving_piece and moving_piece.piece_type == chess.PAWN:

        if chess.square_rank(clicked_square) == 7:

            move = chess.Move(
                selected_square,
                clicked_square,
                promotion=chess.QUEEN
            )

    # legal move
    if move in board.legal_moves:

        board.push(move)

        draw_board()
        root.update()

        # AI move
        if not board.is_game_over():

            root.after(300)

            ai_move()

            draw_board()

    selected_square = None

    # GAME OVER
    if board.is_game_over():

        result = board.result()

        if result == "1-0":
            msg = "🏆 White wins!"
        elif result == "0-1":
            msg = "🏆 Black wins!"
        else:
            msg = "🤝 Draw!"

        messagebox.showinfo("Game Over", msg)

# =====================================================
# NEW GAME
# =====================================================

def new_game():

    global board

    while True:

        fen = random.choice(positions)
        temp_board = chess.Board(fen)

        if temp_board.turn == HUMAN_COLOR:

            board = temp_board
            break

    draw_board()

# =====================================================
# BUTTONS
# =====================================================

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

new_game_button = tk.Button(
    button_frame,
    text="🎲 New Position",
    command=new_game,
    font=("Arial", 14)
)

new_game_button.pack()

# =====================================================
# START
# =====================================================

canvas.bind("<Button-1>", on_click)

draw_board()

root.mainloop()
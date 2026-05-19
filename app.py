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

ANIMATION_DELAY = 15

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
# TKINTER
# =====================================================

root = tk.Tk()
root.title("♟ PPO Chess Endgame Agent")

canvas = tk.Canvas(root, width=BOARD_SIZE, height=BOARD_SIZE)
canvas.pack()

selected_square = None
legal_targets = []

last_move = None

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

def draw_board(animated_piece=None, x=None, y=None):

    canvas.delete("all")

    colors = ["#f0d9b5", "#b58863"]

    for rank in range(8):

        for file in range(8):

            x1 = file * SQUARE_SIZE
            y1 = (7 - rank) * SQUARE_SIZE

            x2 = x1 + SQUARE_SIZE
            y2 = y1 + SQUARE_SIZE

            square = chess.square(file, rank)

            color = colors[(rank + file) % 2]

            # =================================================
            # LAST MOVE HIGHLIGHT
            # =================================================

            if last_move:

                if square == last_move.from_square or square == last_move.to_square:
                    color = "#f7ec59"

            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                outline=color
            )

            # =================================================
            # SELECTED SQUARE
            # =================================================

            if selected_square == square:

                canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill="#74b9ff",
                    stipple="gray50",
                    outline=""
                )

            piece = board.piece_at(square)

            if piece:

                # don't draw moving piece during animation
                if animated_piece and square == animated_piece["from"]:
                    continue

                canvas.create_image(
                    x1,
                    y1,
                    anchor=tk.NW,
                    image=piece_images[piece.symbol()]
                )

    # =================================================
    # LEGAL MOVE DOTS
    # =================================================

    for square in legal_targets:

        file = chess.square_file(square)
        rank = chess.square_rank(square)

        cx = file * SQUARE_SIZE + SQUARE_SIZE // 2
        cy = (7 - rank) * SQUARE_SIZE + SQUARE_SIZE // 2

        canvas.create_oval(
            cx - 10,
            cy - 10,
            cx + 10,
            cy + 10,
            fill="#2ecc71",
            outline=""
        )

    # =================================================
    # ANIMATED PIECE
    # =================================================

    if animated_piece:

        canvas.create_image(
            x,
            y,
            anchor=tk.NW,
            image=piece_images[animated_piece["symbol"]]
        )

# =====================================================
# ANIMATE MOVE
# =====================================================

def animate_move(move):

    moving_piece = board.piece_at(move.from_square)

    if not moving_piece:
        return

    start_file = chess.square_file(move.from_square)
    start_rank = chess.square_rank(move.from_square)

    end_file = chess.square_file(move.to_square)
    end_rank = chess.square_rank(move.to_square)

    start_x = start_file * SQUARE_SIZE
    start_y = (7 - start_rank) * SQUARE_SIZE

    end_x = end_file * SQUARE_SIZE
    end_y = (7 - end_rank) * SQUARE_SIZE

    steps = 20

    for i in range(steps):

        t = (i + 1) / steps

        current_x = start_x + (end_x - start_x) * t
        current_y = start_y + (end_y - start_y) * t

        draw_board(
            animated_piece={
                "from": move.from_square,
                "symbol": moving_piece.symbol()
            },
            x=current_x,
            y=current_y
        )

        root.update()
        root.after(ANIMATION_DELAY)

# =====================================================
# PROMOTION WINDOW
# =====================================================

def choose_promotion():

    result = {"piece": chess.QUEEN}

    window = tk.Toplevel(root)
    window.title("Choose Promotion")
    window.geometry("420x120")
    window.grab_set()

    pieces = [
        ("♕ Queen", chess.QUEEN),
        ("♖ Rook", chess.ROOK),
        ("♗ Bishop", chess.BISHOP),
        ("♘ Knight", chess.KNIGHT),
    ]

    def select(piece_type):

        result["piece"] = piece_type
        window.destroy()

    for i, (text, piece_type) in enumerate(pieces):

        button = tk.Button(
            window,
            text=text,
            font=("Arial", 16),
            width=8,
            command=lambda p=piece_type: select(p)
        )

        button.grid(row=0, column=i, padx=5, pady=25)

    root.wait_window(window)

    return result["piece"]

# =====================================================
# AI MOVE
# =====================================================

def ai_move():

    global board
    global last_move

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

    animate_move(move)

    board.push(move)

    last_move = move

# =====================================================
# CLICK HANDLER
# =====================================================

def on_click(event):

    global selected_square
    global legal_targets
    global last_move

    if board.is_game_over():
        return

    if board.turn != HUMAN_COLOR:
        return

    file = event.x // SQUARE_SIZE
    rank = 7 - (event.y // SQUARE_SIZE)

    clicked_square = chess.square(file, rank)

    clicked_piece = board.piece_at(clicked_square)

    # =================================================
    # NO PIECE SELECTED
    # =================================================

    if selected_square is None:

        if clicked_piece and clicked_piece.color == HUMAN_COLOR:

            selected_square = clicked_square

            legal_targets = []

            for move in board.legal_moves:

                if move.from_square == selected_square:
                    legal_targets.append(move.to_square)

            draw_board()

        return

    # =================================================
    # CLICKED ANOTHER OWN PIECE
    # =================================================

    if clicked_piece and clicked_piece.color == HUMAN_COLOR:

        selected_square = clicked_square

        legal_targets = []

        for move in board.legal_moves:

            if move.from_square == selected_square:
                legal_targets.append(move.to_square)

        draw_board()

        return

    # =================================================
    # TRY MOVE
    # =================================================

    move = chess.Move(selected_square, clicked_square)

    moving_piece = board.piece_at(selected_square)

    # =================================================
    # PROMOTION
    # =================================================

    if moving_piece and moving_piece.piece_type == chess.PAWN:

        if chess.square_rank(clicked_square) == 7:

            promotion_piece = choose_promotion()

            move = chess.Move(
                selected_square,
                clicked_square,
                promotion=promotion_piece
            )

    if move in board.legal_moves:

        # hide dots immediately
        legal_targets = []
        selected_square = None

        draw_board()
        root.update()

        animate_move(move)

        board.push(move)

        last_move = move

        draw_board()
        root.update()

        # AI move
        if not board.is_game_over():

            root.after(200)

            ai_move()

            draw_board()

    # =================================================
    # CLEAR SELECTION
    # =================================================

    selected_square = None
    legal_targets = []

    draw_board()

    # =================================================
    # GAME OVER
    # =================================================

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
    global selected_square
    global legal_targets
    global last_move

    selected_square = None
    legal_targets = []
    last_move = None

    while True:

        fen = random.choice(positions)
        temp_board = chess.Board(fen)

        if temp_board.turn == HUMAN_COLOR:

            board = temp_board
            break

    draw_board()

# =====================================================
# ANIMATION SPEED
# =====================================================

def set_slow():

    global ANIMATION_DELAY
    ANIMATION_DELAY = 35

def set_medium():

    global ANIMATION_DELAY
    ANIMATION_DELAY = 15

def set_fast():

    global ANIMATION_DELAY
    ANIMATION_DELAY = 5

# =====================================================
# BUTTONS
# =====================================================

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

new_game_button = tk.Button(
    button_frame,
    text="🎲 New Position",
    command=new_game,
    font=("Arial", 12)
)

new_game_button.grid(row=0, column=0, padx=5)

slow_button = tk.Button(
    button_frame,
    text="🐢 Slow",
    command=set_slow,
    font=("Arial", 12)
)

slow_button.grid(row=0, column=1, padx=5)

medium_button = tk.Button(
    button_frame,
    text="⚡ Medium",
    command=set_medium,
    font=("Arial", 12)
)

medium_button.grid(row=0, column=2, padx=5)

fast_button = tk.Button(
    button_frame,
    text="🚀 Fast",
    command=set_fast,
    font=("Arial", 12)
)

fast_button.grid(row=0, column=3, padx=5)

# =====================================================
# START
# =====================================================

canvas.bind("<Button-1>", on_click)

draw_board()

root.mainloop()
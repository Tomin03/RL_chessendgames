import streamlit as st
import requests
import chess

from streamlit_chess import st_chess

# =====================================================
# CONFIG
# =====================================================

BACKEND_URL = "http://127.0.0.1:8000"

# =====================================================
# SESSION
# =====================================================

if "board" not in st.session_state:

    response = requests.get(
        f"{BACKEND_URL}/random_position"
    )

    fen = response.json()["fen"]

    st.session_state.board = chess.Board(fen)

# =====================================================
# PAGE
# =====================================================

st.set_page_config(layout="wide")

st.title("♟️ RL Chess Endgames")

col1, col2 = st.columns([1, 2])

# =====================================================
# LEFT PANEL
# =====================================================

with col1:

    st.subheader("Sterowanie")

    if st.button("🎲 NOWA POZYCJA"):

        response = requests.get(
            f"{BACKEND_URL}/random_position"
        )

        fen = response.json()["fen"]

        st.session_state.board = chess.Board(fen)

        st.rerun()

# =====================================================
# BOARD
# =====================================================

with col2:

    board = st.session_state.board

    move = st_chess(
        board.fen(),
        key="chess_board"
    )

    # =========================================
    # PLAYER MOVE
    # =========================================

    if move:

        try:

            chess_move = chess.Move.from_uci(move)

            if chess_move in board.legal_moves:

                board.push(chess_move)

                # =====================================
                # AI MOVE
                # =====================================

                response = requests.post(
                    f"{BACKEND_URL}/ai_move",
                    json={
                        "fen": board.fen()
                    }
                )

                ai_move = response.json()["move"]

                if ai_move:

                    board.push_uci(ai_move)

                st.session_state.board = board

                st.rerun()

        except Exception as e:

            st.error(e)
import requests
import chess
import chess.pgn
import io
import json
import time

# --- KONFIGURACJA ---
USERNAME = "hikaru"
MAX_GAMES = 15000
HEADERS = {
    "User-Agent": f"Python/ChessEndgameScraper (contact: {USERNAME}@example.com)"
}

def is_kings_and_pawns_only(board):
    for piece in board.piece_map().values():
        if piece.piece_type not in [chess.KING, chess.PAWN]:
            return False
    return True

def augment_position(fen):
    """
    Generuje dodatkowe wersje pozycji: 
    1. Oryginał
    2. Odbicie poziome (lewo-prawo)
    3. Odbicie pionowe (zamiana kolorów/stron)
    4. Odbicie poziome + pionowe
    """
    board = chess.Board(fen)
    augmented_fens = {fen} # Używamy set, aby uniknąć duplikatów

    # 1. Odbicie poziome (Horizontal Flip) - np. pionek z a2 trafia na h2
    board_h = board.transform(chess.flip_horizontal)
    augmented_fens.add(board_h.fen())

    # 2. Odbicie pionowe (Vertical Flip / Color Swap) - zamiana stron białych i czarnych
    # Uwaga: chess.flip_vertical zmienia też kolejność ruchu, co jest kluczowe dla RL
    board_v = board.transform(chess.flip_vertical)
    augmented_fens.add(board_v.fen())

    # 3. Oba odbicia naraz
    board_hv = board_h.transform(chess.flip_vertical)
    augmented_fens.add(board_hv.fen())

    return list(augmented_fens)

def fetch_archives(username):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json().get("archives", [])
    except Exception as e:
        print(f"Błąd podczas pobierania archiwów: {e}")
        return []

def fetch_games_from_archive(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json().get("games", [])
    except Exception as e:
        print(f"Błąd podczas pobierania gier z {url}: {e}")
        return []

def extract_positions(pgn_text):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return []

    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
        if is_kings_and_pawns_only(board):
            # Zwracamy listę po augmentacji dla pierwszej znalezionej końcówki
            return augment_position(board.fen())
    return []

def main():
    all_positions = set() # Używamy set globalnie, aby nie powtarzać tych samych pozycji z różnych gier
    game_count = 0

    print(f"Rozpoczynam pobieranie gier dla: {USERNAME}...")
    archives = fetch_archives(USERNAME)

    if not archives:
        print("Brak archiwów.")
        return

    for archive_url in reversed(archives):
        print(f"Przetwarzam: {archive_url.split('/')[-2]}/{archive_url.split('/')[-1]}")
        games = fetch_games_from_archive(archive_url)

        for game in reversed(games):
            if "pgn" not in game:
                continue

            positions = extract_positions(game["pgn"])
            if positions:
                before_count = len(all_positions)
                all_positions.update(positions)
                newly_added = len(all_positions) - before_count
                print(f"Znaleziono końcówkę! Dodano {newly_added} wariantów (Suma: {len(all_positions)})")

            game_count += 1
            if game_count >= MAX_GAMES:
                break
        if game_count >= MAX_GAMES:
            break

    print(f"\nZakończono! Przejrzano {game_count} gier.")
    print(f"Łącznie zebrano {len(all_positions)} unikalnych pozycji (po augmentacji).")

    with open("positions.json", "w") as f:
        json.dump(list(all_positions), f, indent=2)
    print("Dane zapisane w positions.json")

if __name__ == "__main__":
    main()
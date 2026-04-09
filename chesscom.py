import requests
import chess
import chess.pgn
import io
import json

# --- KONFIGURACJA ---
USERNAME = "tomaszygado"  # Twój nick na chess.com
MAX_GAMES = 100           # Ile gier przejrzeć (zaczynając od najnowszych)
HEADERS = {
    "User-Agent": f"Python/ChessEndgameScraper (contact: {USERNAME}@example.com)"
}

def is_kings_and_pawns_only(board):
    """Sprawdza, czy na szachownicy są tylko króle i pionki."""
    for piece in board.piece_map().values():
        if piece.piece_type not in [chess.KING, chess.PAWN]:
            return False
    return True

def fetch_archives(username):
    """Pobiera listę miesięcy, w których gracz grał partie."""
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json().get("archives", [])
    except Exception as e:
        print(f"Błąd podczas pobierania archiwów: {e}")
        return []

def fetch_games_from_archive(url):
    """Pobiera wszystkie partie z danego miesiąca."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json().get("games", [])
    except Exception as e:
        print(f"Błąd podczas pobierania gier z {url}: {e}")
        return []

def extract_positions(pgn_text):
    """Przegląda partię ruch po ruchu i wyciąga końcówki pionowe."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return []

    board = game.board()
    positions = []

    for move in game.mainline_moves():
        board.push(move)
        # Filtr: tylko pionki i króle
        if is_kings_and_pawns_only(board):
            # Aby nie dublować identycznych pozycji (np. po ruchu królem), 
            # bierzemy tylko unikalne FENy w skali jednej partii.
            fen = board.fen()
            if fen not in positions:
                positions.append(fen)

    return positions

def main():
    all_positions = []
    game_count = 0

    print(f"Rozpoczynam pobieranie gier dla użytkownika: {USERNAME}...")
    archives = fetch_archives(USERNAME)

    if not archives:
        print("Brak archiwów lub użytkownik nie istnieje.")
        return

    # Odwracamy listę, aby zacząć od najnowszych partii
    for archive_url in reversed(archives):
        print(f"Przetwarzam miesiąc: {archive_url.split('/')[-2]}/{archive_url.split('/')[-1]}")
        games = fetch_games_from_archive(archive_url)

        for game in reversed(games): # Od najnowszych w danym miesiącu
            if "pgn" not in game:
                continue

            positions = extract_positions(game["pgn"])
            if positions:
                all_positions.extend(positions)
                print(f"Znaleziono końcówkę! (Pobrano już łącznie: {len(all_positions)} pozycji)")

            game_count += 1
            if game_count >= MAX_GAMES:
                break

        if game_count >= MAX_GAMES:
            break

    print(f"\nZakończono! Przejrzano {game_count} gier.")
    print(f"Łącznie zebrano {len(all_positions)} unikalnych pozycji FEN.")

    # Zapis do pliku
    with open("positions.json", "w") as f:
        json.dump(all_positions, f, indent=2)
    print("Dane zapisane w positions.json")

if __name__ == "__main__":
    main()
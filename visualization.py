import json
import os

# 1. Wczytanie danych z pliku positions.json
try:
    with open("positions.json", "r", encoding="utf-8") as f:
        fen_list = json.load(f)
    print(f"Pomyślnie wczytano {len(fen_list)} pozycji z pliku positions.json")
except FileNotFoundError:
    print("Błąd: Nie znaleziono pliku positions.json! Uruchom najpierw skrypt pobierający.")
    fen_list = []
except Exception as e:
    print(f"Wystąpił błąd podczas wczytywania pliku: {e}")
    fen_list = []

def parse_fen(fen):
    board_part = fen.split(' ')[0]
    rows = board_part.split('/')
    parsed_rows = []
    for row in rows:
        parsed_row = []
        for char in row:
            if char.isdigit():
                parsed_row.extend([''] * int(char))
            else:
                parsed_row.append(char)
        parsed_rows.append(parsed_row)
    return parsed_rows

# Mapowanie figur na czytelne obrazy
piece_img = {
    'k': 'https://upload.wikimedia.org/wikipedia/commons/f/f0/Chess_kdt45.svg',
    'p': 'https://upload.wikimedia.org/wikipedia/commons/c/c7/Chess_pdt45.svg',
    'K': 'https://upload.wikimedia.org/wikipedia/commons/4/42/Chess_klt45.svg',
    'P': 'https://upload.wikimedia.org/wikipedia/commons/4/45/Chess_plt45.svg'
}

html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Wizualizacja Końcówek Szachowych</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #1a2634; 
            color: white; 
            padding: 40px;
            margin: 0;
        }}
        h1 {{ text-align: center; color: #f1c40f; margin-bottom: 40px; }}
        
        .grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
            gap: 40px; 
            justify-items: center;
        }}
        
        .board-container {{ 
            background: #263547; 
            padding: 20px; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            width: 280px;
            transition: transform 0.2s;
        }}
        .board-container:hover {{ transform: translateY(-5px); }}

        .meta {{ 
            margin-bottom: 15px; 
            font-weight: bold; 
            text-align: center; 
            font-size: 1.1em;
            color: #f1c40f; 
        }}

        .board {{ 
            display: grid; 
            grid-template-columns: repeat(8, 35px); 
            grid-template-rows: repeat(8, 35px); 
            border: 2px solid #111; 
            margin: 0 auto;
            user-select: none;
        }}

        .cell {{ 
            width: 35px; 
            height: 35px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }}
        
        .white {{ background-color: #ebecd0; }}
        .black {{ background-color: #779556; }}

        .cell img {{
            width: 90%;
            height: 90%;
        }}

        .fen-text {{ 
            font-family: monospace;
            font-size: 11px; 
            color: #8b9eb7; 
            background: #1e2a3a;
            padding: 8px;
            border-radius: 4px;
            margin-top: 15px; 
            display: block; 
            text-align: center;
            overflow-wrap: break-word;
        }}
    </style>
</head>
<body>
    <h1>Moja Baza Końcówek Pionowych ({count})</h1>
    <div class="grid">
        {content}
    </div>
</body>
</html>
"""

board_html = ""
for i, fen in enumerate(fen_list):
    try:
        parsed = parse_fen(fen)
        # Chess.com FENy mają informację o ruchu: 'w' (white) lub 'b' (black)
        turn = "Białe" if " w " in fen or fen.split()[1] == 'w' else "Czarne"
        
        cells = ""
        for r in range(8):
            for c in range(8):
                color_class = "white" if (r + c) % 2 == 0 else "black"
                piece_key = parsed[r][c]
                piece_html = f'<img src="{piece_img[piece_key]}">' if piece_key in piece_img else ""
                cells += f'<div class="cell {color_class}">{piece_html}</div>'
        
        board_html += f"""
        <div class="board-container">
            <div class="meta">Pozycja {i+1} ({turn})</div>
            <div class="board">{cells}</div>
            <div class="fen-text">{fen}</div>
        </div>
        """
    except Exception as e:
        print(f"Pominięto błędny FEN na pozycji {i+1}: {e}")

# Zapisanie gotowego pliku HTML
if board_html:
    with open("szachowe_koncowki.html", "w", encoding="utf-8") as f:
        f.write(html_template.format(content=board_html, count=len(fen_list)))
    print("Gotowe! Otwórz plik szachowe_koncowki.html w przeglądarce.")
else:
    print("Nie wygenerowano żadnych plansz – sprawdź czy positions.json zawiera poprawne FENy.")
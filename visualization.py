import json

# Twoje dane FEN (zachowane bez zmian)
fen_list = [
    "8/p4pk1/1p4p1/4p3/4P3/8/PP4PP/6K1 w - - 0 29",
    "8/p4pk1/1p4p1/4p3/4P3/8/PP3KPP/8 b - - 1 29",
    "8/p4p2/1p3kp1/4p3/4P3/8/PP3KPP/8 w - - 2 30",
    "8/p4p2/1p3kp1/4p3/4P3/5K2/PP4PP/8 b - - 3 30",
    "8/p4p2/1p4p1/4p1k1/4P3/5K2/PP4PP/8 w - - 4 31",
    "8/p4p2/1p4p1/4p1k1/4P3/5KP1/PP5P/8 b - - 0 31",
    "8/p7/1p4p1/4ppk1/4P3/5KP1/PP5P/8 w - - 0 32",
    "8/p7/1p4p1/4pPk1/8/5KP1/PP5P/8 b - - 0 32",
    "8/p7/1p6/4ppk1/8/5KP1/PP5P/8 w - - 0 33",
    "8/p7/1p6/4ppk1/7P/5KP1/PP6/8 b - - 0 33",
    "8/p7/1p6/4pp1k/7P/5KP1/PP6/8 w - - 1 34",
    "8/p7/1p6/4pp1k/7P/4K1P1/PP6/8 b - - 2 34",
    "8/p7/1p6/4pp2/6kP/4K1P1/PP6/8 w - - 3 35",
    "8/p7/1p6/4pp2/6kP/6P1/PP2K3/8 b - - 4 35",
    "8/p7/1p6/4p3/5pkP/6P1/PP2K3/8 w - - 0 36",
    "8/p7/1p6/4p3/5PkP/8/PP2K3/8 b - - 0 36",
    "8/p7/1p6/8/5pkP/8/PP2K3/8 w - - 0 37",
    "8/p7/1p6/7P/5pk1/8/PP2K3/8 b - - 0 37",
    "8/p7/1p6/7k/5p2/8/PP2K3/8 w - - 0 38",
    "8/p7/1p6/7k/5p2/5K2/PP6/8 b - - 1 38",
    "8/p7/1p6/6k1/5p2/5K2/PP6/8 w - - 2 39",
    "8/p7/1p6/6k1/1P3p2/5K2/P7/8 b - - 0 39",
    "8/p7/8/1p4k1/1P3p2/5K2/P7/8 w - - 0 40",
    "8/p7/8/1p4k1/1P3p2/P4K2/8/8 b - - 0 40",
    "8/p7/8/1p3k2/1P3p2/P4K2/8/8 w - - 1 41",
    "8/8/7p/3k2p1/5pPP/5K2/5P2/8 w - - 0 42",
    "8/8/7p/3k2P1/5pP1/5K2/5P2/8 b - - 0 42",
    "8/8/8/3k2p1/5pP1/5K2/5P2/8 w - - 0 43",
    "8/8/8/3k2p1/5pP1/8/4KP2/8 b - - 1 43",
    "8/8/8/6p1/3k1pP1/8/4KP2/8 w - - 2 44",
    "8/8/8/6p1/3k1pP1/8/3K1P2/8 b - - 3 44",
    "8/8/8/6p1/4kpP1/8/3K1P2/8 w - - 4 45",
    "8/8/8/6p1/4kpP1/8/4KP2/8 b - - 5 45",
    "8/8/8/6p1/4k1P1/5p2/4KP2/8 w - - 0 46",
    "8/8/8/6p1/4k1P1/5p2/5P2/5K2 b - - 1 46",
    "8/8/8/6p1/5kP1/5p2/5P2/5K2 w - - 2 47",
    "8/8/8/8/6pk/8/Pp4K1/8 w - - 0 58",
    "6k1/5pp1/p1p1p2p/8/1P6/P6P/5PP1/6K1 w - - 0 30",
    "6k1/5pp1/p1p1p2p/8/1P6/P6P/5PP1/5K2 b - - 1 30",
    "5k2/5pp1/p1p1p2p/8/1P6/P6P/5PP1/5K2 w - - 2 31",
    "5k2/5pp1/p1p1p2p/8/1P6/P6P/4KPP1/8 b - - 3 31",
    "8/4kpp1/p1p1p2p/8/1P6/P6P/4KPP1/8 w - - 4 32",
    "8/4kpp1/p1p1p2p/8/1P6/P3K2P/5PP1/8 b - - 5 32",
    "8/5pp1/p1pkp2p/8/1P6/P3K2P/5PP1/8 w - - 6 33",
    "8/5pp1/p1pkp2p/8/1P1K4/P6P/5PP1/8 b - - 7 33",
    "8/5pp1/p1pk3p/4p3/1P1K4/P6P/5PP1/8 w - - 0 34",
    "8/5pp1/p1pk3p/4p3/1P2K3/P6P/5PP1/8 b - - 1 34",
    "8/5pp1/p1p1k2p/4p3/1P2K3/P6P/5PP1/8 w - - 2 35",
    "8/5pp1/p1p1k2p/4p3/1P2K1P1/P6P/5P2/8 b - - 0 35",
    "8/5p2/p1p1k1pp/4p3/1P2K1P1/P6P/5P2/8 w - - 0 36",
    "8/5p2/p1p1k1pp/4p3/1P2K1PP/P7/5P2/8 b - - 0 36",
    "8/8/p1p1k1pp/4pp2/1P2K1PP/P7/5P2/8 w - - 0 37",
    "8/8/p1p1k1pp/4pP2/1P2K2P/P7/5P2/8 b - - 0 37",
    "8/8/p1p1k2p/4pp2/1P2K2P/P7/5P2/8 w - - 0 38",
    "8/8/p1p1k2p/4pp2/1P5P/P3K3/5P2/8 b - - 1 38",
    "8/8/p1p4p/3kpp2/1P5P/P3K3/5P2/8 w - - 2 39",
    "8/8/p1p4p/3kpp2/1P5P/P2K4/5P2/8 b - - 3 39",
    "8/8/p1p4p/3k1p2/1P2p2P/P2K4/5P2/8 w - - 0 40",
    "8/8/p1p4p/3k1p2/1P2p2P/P3K3/5P2/8 b - - 1 40",
    "8/8/p1p4p/4kp2/1P2p2P/P3K3/5P2/8 w - - 2 41",
    "8/8/p1p4p/4kp2/1P2p2P/P7/3K1P2/8 b - - 3 41",
    "8/8/p1p4p/5p2/1P2pk1P/P7/3K1P2/8 w - - 4 42",
    "8/8/p1p4p/5p2/1P2pk1P/P7/4KP2/8 b - - 5 42",
    "8/8/p1p4p/5p2/1P2p1kP/P7/4KP2/8 w - - 6 43",
    "8/8/p1p4p/5p2/1P2p1kP/P3K3/5P2/8 b - - 7 43",
    "8/8/p1p4p/5p2/1P2p2k/P3K3/5P2/8 w - - 0 44",
    "8/8/p1p4p/5p2/PP2p2k/4K3/5P2/8 b - - 0 44",
    "8/8/p1p4p/5p2/PP2p1k1/4K3/5P2/8 w - - 1 45",
    "8/8/p1p4p/5p2/PP1Kp1k1/8/5P2/8 b - - 2 45",
    "8/8/p1p5/5p1p/PP1Kp1k1/8/5P2/8 w - - 0 46",
    "8/8/p1p5/2K2p1p/PP2p1k1/8/5P2/8 b - - 1 46",
    "8/8/p1p5/2K2p2/PP2p1kp/8/5P2/8 w - - 0 47",
    "8/8/p1K5/5p2/PP2p1kp/8/5P2/8 b - - 0 47",
    "8/8/p1K5/5p2/PP2p1k1/7p/5P2/8 w - - 0 48",
    "8/8/p1K5/1P3p2/P3p1k1/7p/5P2/8 b - - 0 48",
    "8/8/2K5/1p3p2/P3p1k1/7p/5P2/8 w - - 0 49",
    "8/8/2K5/1P3p2/4p1k1/7p/5P2/8 b - - 0 49",
    "8/8/2K5/1P3p2/4p1k1/8/5P1p/8 w - - 0 50",
    "8/8/1PK5/5p2/4p1k1/8/5P1p/8 b - - 0 50",
    "1K6/8/8/5p2/4p3/5k2/5P2/8 b - - 0 54",
    "1K6/8/8/5p2/4p3/8/5k2/8 w - - 0 55",
    "8/7p/4k3/5pP1/5P2/4K3/8/8 b - - 0 56",
    "8/5k1p/8/5pP1/5P2/4K3/8/8 w - - 1 57",
    "8/5k1p/8/5pP1/3K1P2/8/8/8 b - - 2 57",
    "8/7p/6k1/5pP1/3K1P2/8/8/8 w - - 3 58",
    "8/7p/6k1/4KpP1/5P2/8/8/8 b - - 4 58",
    "8/7p/8/4KpPk/5P2/8/8/8 w - - 5 59",
    "8/7p/8/5KPk/5P2/8/8/8 b - - 0 59",
    "8/8/7p/5KPk/5P2/8/8/8 w - - 0 60",
    "8/8/6Pp/5K1k/5P2/8/8/8 b - - 0 60",
    "8/8/6Pp/5K2/5P1k/8/8/8 w - - 1 61",
    "8/6P1/7p/5K2/5P1k/8/8/8 b - - 0 61",
    "8/6P1/8/5K1p/5P1k/8/8/8 w - - 0 62",
    "8/K7/8/5p2/5P2/4k1P1/7P/8 b - - 0 57",
    "8/K7/8/5p2/5P2/5kP1/7P/8 w - - 1 58",
    "8/1K6/8/5p2/5P2/5kP1/7P/8 b - - 2 58",
    "8/1K6/8/5p2/5Pk1/6P1/7P/8 w - - 3 59",
    "8/8/2K5/5p2/5Pk1/6P1/7P/8 b - - 4 59",
    "8/8/2K5/5p2/5P2/6Pk/7P/8 w - - 5 60",
    "8/8/8/3K1p2/5P2/6Pk/7P/8 b - - 6 60",
    "8/8/8/3K1p2/5P2/6P1/7k/8 w - - 0 61",
    "8/8/8/3K1p2/5PP1/8/7k/8 b - - 0 61",
    "8/8/8/3K1p2/5PP1/6k1/8/8 w - - 1 62",
    "8/8/8/3K1pP1/5P2/6k1/8/8 b - - 0 62",
    "8/8/8/3K1pP1/5k2/8/8/8 w - - 0 63",
    "8/8/6P1/3K1p2/5k2/8/8/8 b - - 0 63",
    "8/8/6P1/3K1pk1/8/8/8/8 w - - 1 64",
    "8/6P1/8/3K1pk1/8/8/8/8 b - - 0 64",
    "8/6P1/5k2/3K1p2/8/8/8/8 w - - 1 65",
    "8/8/3k4/1p3p2/p7/P3P1P1/1P1K1P1P/8 w - - 0 38",
    "8/8/3k4/1p3p2/p6P/P3P1P1/1P1K1P2/8 b - - 0 38",
    "8/8/8/1p2kp2/p6P/P3P1P1/1P1K1P2/8 w - - 1 39",
    "8/8/8/1p2kp2/p6P/P3PPP1/1P1K4/8 b - - 0 39",
    "8/8/8/1p2k3/p4p1P/P3PPP1/1P1K4/8 w - - 0 40",
    "8/8/8/1p2k3/p4P1P/P4PP1/1P1K4/8 b - - 0 40",
    "8/8/5k2/1p6/p4P1P/P4PP1/1P1K4/8 w - - 1 41",
    "8/8/5k2/1p6/p4P1P/P2K1PP1/1P6/8 b - - 2 41",
    "8/8/5k2/8/pp3P1P/P2K1PP1/1P6/8 w - - 0 42",
    "8/8/5k2/8/pP3P1P/3K1PP1/1P6/8 b - - 0 42",
    "8/8/5k2/8/1P3P1P/p2K1PP1/1P6/8 w - - 0 43",
    "8/8/5k2/8/1P3P1P/P2K1PP1/8/8 b - - 0 43",
    "8/8/4k3/8/1P3P1P/P2K1PP1/8/8 w - - 1 44",
    "8/8/4k3/8/PP3P1P/3K1PP1/8/8 b - - 0 44",
    "8/8/3k4/8/PP3P1P/3K1PP1/8/8 w - - 1 45",
    "8/8/3k4/8/PP1K1P1P/5PP1/8/8 b - - 2 45",
    "8/2k5/8/8/PP1K1P1P/5PP1/8/8 w - - 3 46",
    "8/2k5/8/8/PP1K1PPP/5P2/8/8 b - - 0 46",
    "8/8/3k4/8/PP1K1PPP/5P2/8/8 w - - 1 47",
    "8/8/3k4/5P2/PP1K2PP/5P2/8/8 b - - 0 47",
    "8/8/2k5/5P2/PP1K2PP/5P2/8/8 w - - 1 48",
    "8/8/2k5/5PP1/PP1K3P/5P2/8/8 b - - 0 48",
    "8/8/3k4/5PP1/PP1K3P/5P2/8/8 w - - 1 49",
    "8/8/3k4/5PPP/PP1K4/5P2/8/8 b - - 0 49",
    "8/3k4/8/5PPP/PP1K4/5P2/8/8 w - - 1 50",
    "8/3k4/6P1/5P1P/PP1K4/5P2/8/8 b - - 0 50",
    "8/8/3k2P1/5P1P/PP1K4/5P2/8/8 w - - 1 51",
    "8/8/3k2PP/5P2/PP1K4/5P2/8/8 b - - 0 51",
    "8/8/2k3PP/5P2/PP1K4/5P2/8/8 w - - 1 52",
    "8/7P/2k3P1/5P2/PP1K4/5P2/8/8 b - - 0 52",
    "8/2k4P/6P1/5P2/PP1K4/5P2/8/8 w - - 1 53",
    "8/8/5P2/6Pp/7P/4k1K1/8/8 b - - 0 108"
]


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

# Mapowanie figur na czytelne obrazy (Wikipedia/Wikimedia dla stabilności)
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
    <title>Wizualizacja Koncówek Szachowych</title>
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
        
        /* Kolory pól wzorowane na zdjęciu */
        .white {{ background-color: #ebecd0; }}
        .black {{ background-color: #779556; }} /* Klasyczny zielony Chess.com */
        /* Alternatywny fioletowy ze zdjęcia: .black {{ background-color: #7d67b8; }} */

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
    <h1>Analiza Końcówek Szachowych</h1>
    <div class="grid">
        {content}
    </div>
</body>
</html>
"""

board_html = ""
for i, fen in enumerate(fen_list):
    parsed = parse_fen(fen)
    turn = "Białe" if " w " in fen else "Czarne"
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

with open("szachowe_koncowki.html", "w", encoding="utf-8") as f:
    f.write(html_template.format(content=board_html))

print("Zaktualizowano! Otwórz plik szachowe_koncowki.html.")
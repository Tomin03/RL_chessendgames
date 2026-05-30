# RL Chess Endgames

Projekt do nauki i testowania agenta reinforcement learning w szachowych koncowkach pionowych. Aplikacja sklada sie z backendu FastAPI, modelu PPO trenowanego w srodowisku Gymnasium oraz frontendu React/Vite, w ktorym uzytkownik moze rozegrac losowa koncowke przeciwko agentowi.

## Funkcje

- losowanie pozycji koncowkowych z pliku `backend/positions.json`,
- gra na interaktywnej szachownicy w przegladarce,
- ruchy agenta generowane przez model `MaskablePPO`,
- obsluga legalnych ruchow, promocji pionka, historii ruchow i cofania,
- podpowiedz ruchu od agenta RL,
- skrypty do pobierania pozycji, wizualizacji danych, trenowania i ewaluacji modelu.

## Struktura projektu

```text
RL_chessendgames/
|-- backend/
|   |-- main.py                # API FastAPI uzywane przez frontend
|   |-- env_ppo.py             # srodowisko Gymnasium dla koncowek szachowych
|   |-- positions.json         # baza pozycji FEN
|   `-- ppo_chess_model.zip    # wytrenowany model PPO
|-- frontend/
|   |-- src/App.jsx            # glowny interfejs aplikacji
|   |-- src/App.css            # style aplikacji
|   `-- package.json           # zaleznosci i skrypty Vite
|-- model.py                   # trenowanie, ewaluacja i demo agenta
|-- chesscom.py                # pobieranie pozycji z partii Chess.com
|-- visualization.py           # generowanie HTML z pozycjami
|-- requirements.txt           # zaleznosci Pythona
`-- evaluation_results.txt     # zapis wynikow ewaluacji
```

## Wymagania

- Python 3.10 lub nowszy,
- Node.js i npm,
- opcjonalnie CUDA, jezeli trening ma korzystac z GPU.

Backend korzysta m.in. z bibliotek `fastapi`, `uvicorn`, `python-chess`, `gymnasium`, `stable-baselines3`, `sb3-contrib`, `torch` i `numpy`. Frontend korzysta z Reacta, Vite, `chess.js` oraz `react-chessboard`.

## Instalacja

1. Utworz i aktywuj srodowisko Pythona:

```bash
python -m venv venv
venv\Scripts\activate
```

2. Zainstaluj zaleznosci backendu i modelu:

```bash
pip install -r requirements.txt
```

3. Zainstaluj zaleznosci frontendu:

```bash
cd frontend
npm install
```

## Uruchomienie aplikacji

Najpierw uruchom backend z glownego katalogu projektu:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Nastepnie w drugim terminalu uruchom frontend:

```bash
cd frontend
npm run dev
```

Po starcie Vite otworz adres pokazany w terminalu, zwykle:

```text
http://localhost:5173
```

Frontend komunikuje sie z backendem pod adresem `http://127.0.0.1:8000`.

## Endpointy API

Backend udostepnia trzy podstawowe endpointy:

- `GET /` - sprawdzenie, czy backend dziala,
- `GET /random_position` - zwraca losowa poprawna pozycje FEN,
- `POST /ai_move` - przyjmuje pozycje FEN i zwraca ruch agenta.

Przyklad zapytania do agenta:

```json
{
  "fen": "8/8/8/3k4/8/4K3/3P4/8 w - - 0 1"
}
```

Przykladowa odpowiedz:

```json
{
  "move": "d2d4",
  "fen": "8/8/8/3k4/8/3PK3/8/8 b - - 0 1",
  "gameOver": false,
  "result": null
}
```

## Trenowanie modelu

Trening uruchamia skrypt `model.py`. Domyslnie model jest zapisywany jako `backend/ppo_chess_model`.

```bash
python model.py --mode train
```

Mozna zmienic liczbe krokow treningu i liczbe rownoleglych srodowisk:

```bash
python model.py --mode train --timesteps 2000000 --n-envs 4
```

Srodowisko treningowe znajduje sie w `backend/env_ppo.py`. Obserwacja ma ksztalt `8 x 8 x 13`: dwanascie kanalow opisuje figury, a ostatni kanal opisuje strone na ruchu. Przestrzen akcji zawiera ruchy UCI wygenerowane dla wszystkich pol startowych, docelowych oraz promocji.

## Ewaluacja i demo

Ewaluacja modelu:

```bash
python model.py --mode eval --games 50
```

Wyniki sa dopisywane do pliku `evaluation_results.txt`.

Demo gry agenta w konsoli:

```bash
python model.py --mode play
```

## Dane pozycji

Plik `backend/positions.json` zawiera liste pozycji FEN uzywanych przez backend i srodowisko treningowe. Pozycje moga pochodzic ze skryptu `chesscom.py`, ktory pobiera partie z publicznego API Chess.com, wyszukuje koncowki z krolami i pionami, a nastepnie tworzy dodatkowe warianty przez odbicia planszy.

Uruchomienie pobierania:

```bash
python chesscom.py
```

Uwaga: skrypt zapisuje wynik do `positions.json` w katalogu, z ktorego zostal uruchomiony. Jezeli dane maja byc uzyte przez backend, umiesc je w `backend/positions.json`.

## Wizualizacja pozycji

Skrypt `visualization.py` generuje plik HTML z podgladem pozycji:

```bash
python visualization.py
```

Wynik jest zapisywany jako `szachowe_koncowki.html`.

## Typowy workflow

1. Zbierz lub przygotuj pozycje FEN.
2. Umiesc dane w `backend/positions.json`.
3. Wytrenuj model poleceniem `python model.py --mode train`.
4. Uruchom backend FastAPI.
5. Uruchom frontend Vite i testuj agenta w przegladarce.

## Uwagi

- Plik modelu `backend/ppo_chess_model.zip` musi istniec, aby backend mogl wystartowac.
- Backend filtruje pozycje i odrzuca niepoprawne, zakonczone albo pozbawione legalnych ruchow.
- Jezeli model zwroci nielegalny ruch lub wystapi blad predykcji, backend wybiera losowy legalny ruch jako zabezpieczenie.
- Stockfish nie jest wymagany do obecnej wersji aplikacji, ale `requirements.txt` zawiera notatke o mozliwej integracji z zewnetrznym binarium silnika.

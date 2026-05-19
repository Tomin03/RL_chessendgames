import { useEffect, useMemo, useState } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const animationOptions = [
  { label: "Wolny", value: 900 },
  { label: "Sredni", value: 300 },
  { label: "Szybki", value: 80 },
];

function colorName(color) {
  return color === "w" ? "biale" : "czarne";
}

function uciToMove(uci) {
  return {
    from: uci.slice(0, 2),
    to: uci.slice(2, 4),
    promotion: uci.slice(4, 5) || undefined,
  };
}

function getBoardWidth() {
  if (typeof window === "undefined") return 680;
  if (window.innerWidth < 760) {
    return Math.max(300, Math.min(window.innerWidth - 32, 560));
  }
  return Math.max(420, Math.min(window.innerWidth - 420, 720));
}

function App() {
  const [game, setGame] = useState(new Chess());
  const [playerColor, setPlayerColor] = useState("white");
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [animationSpeed, setAnimationSpeed] = useState(300);
  const [boardWidth, setBoardWidth] = useState(getBoardWidth);
  const [isLoading, setIsLoading] = useState(true);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [lastMove, setLastMove] = useState(null);
  const [message, setMessage] = useState("Losuje pozycje...");

  const playerTurn = playerColor === "white" ? "w" : "b";
  const isPlayerTurn = game.turn() === playerTurn;
  const gameOver = game.isGameOver();

  useEffect(() => {
    function handleResize() {
      setBoardWidth(getBoardWidth());
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  async function loadRandomPosition() {
    setIsLoading(true);
    setIsAiThinking(false);
    setSelectedSquare(null);
    setLastMove(null);
    setMessage("Losuje pozycje...");

    try {
      const response = await fetch(`${API_URL}/random_position`);
      if (!response.ok) throw new Error("Nie udalo sie pobrac pozycji");

      const data = await response.json();
      const newGame = new Chess(data.fen);
      const nextPlayerColor = data.playerColor || (newGame.turn() === "w" ? "white" : "black");

      setGame(newGame);
      setPlayerColor(nextPlayerColor);
      setMessage(`Grasz ${nextPlayerColor === "white" ? "bialymi" : "czarnymi"}. Twoj ruch.`);
    } catch (error) {
      console.error(error);
      setMessage("Backend nie odpowiada. Uruchom FastAPI na porcie 8000.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadRandomPosition();
  }, []);

  function buildStatus(currentGame = game) {
    if (currentGame.isCheckmate()) return "Mat. Partia zakonczona.";
    if (currentGame.isDraw()) return "Remis. Partia zakonczona.";
    if (currentGame.isGameOver()) return "Partia zakonczona.";
    if (currentGame.inCheck()) return `Szach. Na ruchu: ${colorName(currentGame.turn())}.`;
    return `Na ruchu: ${colorName(currentGame.turn())}.`;
  }

  async function requestAiMove(fen) {
    setIsAiThinking(true);
    setMessage("Agent RL mysli...");

    try {
      const response = await fetch(`${API_URL}/ai_move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen }),
      });

      if (!response.ok) throw new Error("Agent nie zwrocil ruchu");

      const data = await response.json();
      if (!data.move) {
        const finishedGame = new Chess(data.fen || fen);
        setGame(finishedGame);
        setMessage(buildStatus(finishedGame));
        setIsAiThinking(false);
        return;
      }

      window.setTimeout(() => {
        const afterAiMove = data.fen ? new Chess(data.fen) : new Chess(fen);
        if (!data.fen) {
          afterAiMove.move(uciToMove(data.move));
        }
        setGame(afterAiMove);
        setLastMove({ from: data.move.slice(0, 2), to: data.move.slice(2, 4) });
        setMessage(buildStatus(afterAiMove));
        setIsAiThinking(false);
      }, animationSpeed);
    } catch (error) {
      console.error(error);
      setMessage("Nie udalo sie pobrac ruchu agenta RL.");
      setIsAiThinking(false);
    }
  }

  function tryPlayerMove(sourceSquare, targetSquare) {
    if (isLoading || isAiThinking || gameOver || !isPlayerTurn) return false;

    const gameCopy = new Chess(game.fen());
    const move = gameCopy.move({
      from: sourceSquare,
      to: targetSquare,
      promotion: "q",
    });

    if (move === null) return false;

    setGame(gameCopy);
    setSelectedSquare(null);
    setLastMove({ from: sourceSquare, to: targetSquare });

    if (gameCopy.isGameOver()) {
      setMessage(buildStatus(gameCopy));
      return true;
    }

    requestAiMove(gameCopy.fen());
    return true;
  }

  function onPieceDrop({ sourceSquare, targetSquare }) {
    return tryPlayerMove(sourceSquare, targetSquare);
  }

  function onSquareClick({ square }) {
    if (isLoading || isAiThinking || gameOver || !isPlayerTurn) return;

    const piece = game.get(square);
    if (!selectedSquare) {
      if (piece && piece.color === playerTurn) {
        setSelectedSquare(square);
      }
      return;
    }

    if (selectedSquare === square) {
      setSelectedSquare(null);
      return;
    }

    if (piece && piece.color === playerTurn) {
      setSelectedSquare(square);
      return;
    }

    if (!tryPlayerMove(selectedSquare, square)) {
      setSelectedSquare(null);
    }
  }

  const squareStyles = useMemo(() => {
    const styles = {};

    if (lastMove) {
      styles[lastMove.from] = { background: "rgba(24, 185, 122, 0.36)" };
      styles[lastMove.to] = { background: "rgba(24, 185, 122, 0.46)" };
    }

    if (selectedSquare) {
      styles[selectedSquare] = {
        ...(styles[selectedSquare] || {}),
        background: "rgba(28, 121, 255, 0.42)",
      };

      for (const move of game.moves({ square: selectedSquare, verbose: true })) {
        styles[move.to] = {
          ...(styles[move.to] || {}),
          background:
            game.get(move.to) && game.get(move.to).color !== playerTurn
              ? "radial-gradient(circle, rgba(220, 38, 38, 0.58) 38%, transparent 42%)"
              : "radial-gradient(circle, rgba(28, 121, 255, 0.52) 18%, transparent 22%)",
        };
      }
    }

    return styles;
  }, [game, lastMove, playerTurn, selectedSquare]);

  const chessboardOptions = useMemo(
    () => ({
      position: game.fen().split(" ")[0],
      onPieceDrop,
      onSquareClick,
      allowDragging: !isLoading && !isAiThinking && isPlayerTurn && !gameOver,
      boardOrientation: playerColor,
      animationDurationInMs: animationSpeed,
      showAnimations: true,
      squareStyles,
      darkSquareStyle: { backgroundColor: "#cf8c43" },
      lightSquareStyle: { backgroundColor: "#f2c58f" },
      boardStyle: {
        width: `${boardWidth}px`,
        maxWidth: "100%",
        borderRadius: "4px",
      },
    }),
    [
      animationSpeed,
      boardWidth,
      game,
      gameOver,
      isAiThinking,
      isLoading,
      isPlayerTurn,
      playerColor,
      squareStyles,
    ],
  );

  return (
    <main className="app-shell">
      <section className="game-layout">
        <aside className="side-panel">
          <button className="new-position-button" onClick={loadRandomPosition} disabled={isLoading}>
            NOWA POZYCJA
          </button>

          <div className="controls">
            <label htmlFor="animation-speed">Wybierz tryb predkosci animacji</label>
            <select
              id="animation-speed"
              value={animationSpeed}
              onChange={(event) => setAnimationSpeed(Number(event.target.value))}
            >
              {animationOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="status-box">
            <span>{isAiThinking ? "Agent RL" : isPlayerTurn ? "Gracz" : "Pozycja"}</span>
            <p>{message}</p>
          </div>
        </aside>

        <div className="board-frame" aria-busy={isLoading || isAiThinking}>
          <Chessboard options={chessboardOptions} />
        </div>
      </section>
    </main>
  );
}

export default App;

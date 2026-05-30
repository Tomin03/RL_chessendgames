import { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";
import { FaChessBishop, FaChessKnight, FaChessQueen, FaChessRook, FaMagic, FaPlus, FaUndo } from "react-icons/fa";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const animationOptions = [
  { label: "Wolny", value: 900 },
  { label: "Średni", value: 300 },
  { label: "Szybki", value: 80 },
];

const promotionOptions = [
  { label: "Hetman", value: "q", Icon: FaChessQueen },
  { label: "Wieża", value: "r", Icon: FaChessRook },
  { label: "Goniec", value: "b", Icon: FaChessBishop },
  { label: "Skoczek", value: "n", Icon: FaChessKnight },
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

function getFenMoveNumber(fen) {
  return Number(fen.split(" ")[5]) || 1;
}

function formatMoveHistory(moves) {
  const rows = [];

  moves.forEach((move, index) => {
    const moveNumber = Math.floor(index / 2) + 1;
    let row = rows[rows.length - 1];

    if (index % 2 === 0 || !row) {
      row = { number: moveNumber, white: null, black: null };
      rows.push(row);
    }

    if (move.color === "w") {
      row.white = move.san;
    } else {
      row.black = move.san;
    }
  });

  return rows;
}

function isPromotionMove(currentGame, sourceSquare, targetSquare) {
  const piece = currentGame.get(sourceSquare);
  if (!piece || piece.type !== "p") return false;

  const promotionRank = piece.color === "w" ? "8" : "1";
  if (!targetSquare.endsWith(promotionRank)) return false;

  return currentGame
    .moves({ square: sourceSquare, verbose: true })
    .some((move) => move.to === targetSquare && move.flags.includes("p"));
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
  const [hintMove, setHintMove] = useState(null);
  const [isHintLoading, setIsHintLoading] = useState(false);
  const [moveHistory, setMoveHistory] = useState([]);
  const [turnSnapshots, setTurnSnapshots] = useState([]);
  const [pendingPromotion, setPendingPromotion] = useState(null);
  const [message, setMessage] = useState("Losuje pozycje...");
  const aiRequestId = useRef(0);
  const hintRequestId = useRef(0);

  const playerTurn = playerColor === "white" ? "w" : "b";
  const isPlayerTurn = game.turn() === playerTurn;
  const gameOver = game.isGameOver();
  const formattedMoveHistory = useMemo(() => formatMoveHistory(moveHistory), [moveHistory]);

  useEffect(() => {
    function handleResize() {
      setBoardWidth(getBoardWidth());
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  async function loadRandomPosition() {
    aiRequestId.current += 1;
    hintRequestId.current += 1;
    setIsLoading(true);
    setIsAiThinking(false);
    setIsHintLoading(false);
    setSelectedSquare(null);
    setLastMove(null);
    setHintMove(null);
    setMoveHistory([]);
    setTurnSnapshots([]);
    setPendingPromotion(null);
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
    const timerId = window.setTimeout(loadRandomPosition, 0);
    return () => window.clearTimeout(timerId);
  }, []);

  function buildStatus(currentGame = game) {
    if (currentGame.isCheckmate()) return "Mat. Partia zakonczona.";
    if (currentGame.isDraw()) return "Remis. Partia zakonczona.";
    if (currentGame.isGameOver()) return "Partia zakonczona.";
    if (currentGame.inCheck()) return `Szach. Na ruchu: ${colorName(currentGame.turn())}.`;
    return `Na ruchu: ${colorName(currentGame.turn())}.`;
  }

  async function requestAiMove(fen, historyBeforeAi) {
    const requestId = aiRequestId.current + 1;
    aiRequestId.current = requestId;
    hintRequestId.current += 1;
    setIsAiThinking(true);
    setHintMove(null);
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
        if (aiRequestId.current !== requestId) return;
        const finishedGame = new Chess(data.fen || fen);
        setGame(finishedGame);
        setMessage(buildStatus(finishedGame));
        setIsAiThinking(false);
        return;
      }

      window.setTimeout(() => {
        if (aiRequestId.current !== requestId) return;
        const aiGameForSan = new Chess(fen);
        const aiTurn = aiGameForSan.turn();
        const aiMoveNumber = getFenMoveNumber(fen);
        const aiMove = aiGameForSan.move(uciToMove(data.move));
        const afterAiMove = data.fen ? new Chess(data.fen) : aiGameForSan;

        setGame(afterAiMove);
        setLastMove({ from: data.move.slice(0, 2), to: data.move.slice(2, 4) });
        setMoveHistory([
          ...historyBeforeAi,
          { san: aiMove?.san || data.move, color: aiMove?.color || aiTurn, number: aiMoveNumber },
        ]);
        setMessage(buildStatus(afterAiMove));
        setIsAiThinking(false);
      }, animationSpeed);
    } catch (error) {
      console.error(error);
      setMessage("Nie udalo sie pobrac ruchu agenta RL.");
      setIsAiThinking(false);
    }
  }

  function completePlayerMove(sourceSquare, targetSquare, promotion) {
    if (isLoading || isAiThinking || gameOver || !isPlayerTurn) return false;

    hintRequestId.current += 1;
    const gameCopy = new Chess(game.fen());
    const moveNumber = getFenMoveNumber(game.fen());
    const move = gameCopy.move({
      from: sourceSquare,
      to: targetSquare,
      promotion,
    });

    if (move === null) return false;

    const historyBeforeMove = moveHistory;
    const nextMoveHistory = [...historyBeforeMove, { san: move.san, color: move.color, number: moveNumber }];

    setTurnSnapshots((snapshots) => [
      ...snapshots,
      {
        fen: game.fen(),
        lastMove,
        moveHistory: historyBeforeMove,
      },
    ]);
    setGame(gameCopy);
    setSelectedSquare(null);
    setPendingPromotion(null);
    setHintMove(null);
    setLastMove({ from: sourceSquare, to: targetSquare });
    setMoveHistory(nextMoveHistory);

    if (gameCopy.isGameOver()) {
      setMessage(buildStatus(gameCopy));
      return true;
    }

    requestAiMove(gameCopy.fen(), nextMoveHistory);
    return true;
  }

  function tryPlayerMove(sourceSquare, targetSquare) {
    if (isLoading || isAiThinking || gameOver || !isPlayerTurn) return false;

    if (isPromotionMove(game, sourceSquare, targetSquare)) {
      setPendingPromotion({ sourceSquare, targetSquare });
      setSelectedSquare(null);
      setMessage("Wybierz figure do promocji pionka.");
      return true;
    }

    return completePlayerMove(sourceSquare, targetSquare);
  }

  async function showHint() {
    if (isLoading || isAiThinking || isHintLoading || gameOver || pendingPromotion) return;

    const fen = game.fen();
    const requestId = hintRequestId.current + 1;
    hintRequestId.current = requestId;
    setIsHintLoading(true);
    setHintMove(null);
    setMessage("Szukam podpowiedzi agenta RL...");

    try {
      const response = await fetch(`${API_URL}/ai_move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen }),
      });

      if (!response.ok) throw new Error("Agent nie zwrocil podpowiedzi");

      const data = await response.json();
      if (hintRequestId.current !== requestId || game.fen() !== fen) return;

      if (!data.move) {
        setMessage("Agent nie znalazl ruchu w tej pozycji.");
        return;
      }

      const hintGame = new Chess(fen);
      const move = hintGame.move(uciToMove(data.move));
      setHintMove({
        from: data.move.slice(0, 2),
        to: data.move.slice(2, 4),
      });
      setMessage(`Podpowiedz agenta: ${move?.san || data.move}.`);
    } catch (error) {
      console.error(error);
      if (hintRequestId.current === requestId) {
        setMessage("Nie udalo sie pobrac podpowiedzi agenta RL.");
      }
    } finally {
      if (hintRequestId.current === requestId) {
        setIsHintLoading(false);
      }
    }
  }

  function choosePromotion(promotion) {
    if (!pendingPromotion) return;
    completePlayerMove(pendingPromotion.sourceSquare, pendingPromotion.targetSquare, promotion);
  }

  function cancelPromotion() {
    setPendingPromotion(null);
    setMessage(buildStatus(game));
  }

  function undoLastMove() {
    if (isLoading || isAiThinking || turnSnapshots.length === 0) return;

    hintRequestId.current += 1;
    const snapshot = turnSnapshots[turnSnapshots.length - 1];
    const restoredGame = new Chess(snapshot.fen);

    setGame(restoredGame);
    setSelectedSquare(null);
    setPendingPromotion(null);
    setHintMove(null);
    setLastMove(snapshot.lastMove);
    setMoveHistory(snapshot.moveHistory);
    setTurnSnapshots((snapshots) => snapshots.slice(0, -1));
    setMessage(`Cofnieto ruch. ${buildStatus(restoredGame)}`);
  }

  function onPieceDrop({ sourceSquare, targetSquare }) {
    return tryPlayerMove(sourceSquare, targetSquare);
  }

  function onSquareClick({ square }) {
    if (isLoading || isAiThinking || gameOver || !isPlayerTurn) return;

    setHintMove(null);
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

  const chessboardOptions = {
    position: game.fen().split(" ")[0],
    onPieceDrop,
    onSquareClick,
    allowDragging: !isLoading && !isAiThinking && isPlayerTurn && !gameOver,
    boardOrientation: playerColor,
    animationDurationInMs: animationSpeed,
    showAnimations: true,
    squareStyles,
    arrows: hintMove ? [{ startSquare: hintMove.from, endSquare: hintMove.to, color: "#14b47a" }] : [],
    arrowOptions: {
      color: "#14b47a",
      secondaryColor: "#07856f",
      tertiaryColor: "#e91658",
      arrowLengthReducerDenominator: 7,
      sameTargetArrowLengthReducerDenominator: 4,
      arrowWidthDenominator: 5.5,
      activeArrowWidthMultiplier: 0.9,
      opacity: 0.78,
      activeOpacity: 0.55,
      arrowStartOffset: 0.08,
    },
    allowDrawingArrows: false,
    clearArrowsOnClick: false,
    clearArrowsOnPositionChange: false,
    darkSquareStyle: { backgroundColor: "#cf8c43" },
    lightSquareStyle: { backgroundColor: "#f2c58f" },
    boardStyle: {
      width: `${boardWidth}px`,
      maxWidth: "100%",
      borderRadius: "4px",
    },
  };

  return (
    <main className="app-shell">
      <h1
        className="app-title"
          style={{fontWeight: "bold",textAlign: "center",marginBottom: "16px",fontSize: "32px"
  }}
>
  KOŃCÓWKI SZACHOWE <br />
  PIONOWE Z AGENTEM RL
        </h1>
      <section className="game-layout">
        <aside className="side-panel">
          <button className="new-position-button" onClick={loadRandomPosition} disabled={isLoading}>
            <span>NOWA POZYCJA</span>
            <FaPlus aria-hidden="true" />
          </button>

          <div className="controlsA">
            <label htmlFor="animation-speed">Tryb prędkości animacji</label>
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

        <aside className="history-panel" aria-label="Historia ruchow">
          <div className="move-history-card">
            <h2>HISTORIA RUCHÓW</h2>
            {formattedMoveHistory.length > 0 ? (
              <ol className="move-history-list">
                {formattedMoveHistory.map((row) => (
                  <li key={row.number}>
                    <span className="move-number">{row.number}.</span>
                    <span>{row.white || ""}</span>
                    {row.black ? <span>{row.black}</span> : <span className="pending-move">...</span>}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="empty-history">Brak ruchow</p>
            )}
          </div>

          <div className="history-actions">
            <button
              className="history-button undo-button"
              onClick={undoLastMove}
              disabled={isLoading || isAiThinking || turnSnapshots.length === 0}
            >
              <span>COFNIJ RUCH</span>
              <FaUndo aria-hidden="true" />
            </button>

            <button
              className="history-button hint-button"
              onClick={showHint}
              disabled={isLoading || isAiThinking || isHintLoading || gameOver || Boolean(pendingPromotion)}
            >
              <span>{isHintLoading ? "SZUKAM..." : "PODPOWIEDZ"}</span>
              <FaMagic aria-hidden="true" />
            </button>
          </div>
        </aside>
      </section>

      {pendingPromotion ? (
        <div className="promotion-overlay" role="dialog" aria-modal="true" aria-label="Wybierz promocje">
          <div className="promotion-dialog">
            <h2>Promocja pionka</h2>
            <div className="promotion-options">
              {promotionOptions.map(({ Icon, ...option }) => (
                <button key={option.value} type="button" onClick={() => choosePromotion(option.value)} aria-label={option.label} title={option.label}>
                  <Icon aria-hidden="true" />
                </button>
              ))}
            </div>
            <button className="promotion-cancel" type="button" onClick={cancelPromotion}>
              Anuluj
            </button>
          </div>
        </div>
      ) : null}
    </main>
  );
}

export default App;

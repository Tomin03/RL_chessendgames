import argparse
import csv
import random
from pathlib import Path

import chess
from torch.distributions import Distribution
from sb3_contrib import MaskablePPO

from backend.env_ppo import ChessEnv, PIECE_VALUES, action_index_to_move, move_to_action_index


Distribution.set_default_validate_args(False)


def choose_agent_color(mode, side_to_move):
    if mode == "white":
        return chess.WHITE
    if mode == "black":
        return chess.BLACK
    if mode == "side-to-move":
        return side_to_move
    return random.choice([chess.WHITE, chess.BLACK])


def material_advantage(board, color):
    score = 0.0
    for piece in board.piece_map().values():
        value = PIECE_VALUES[piece.piece_type]
        score += value if piece.color == color else -value
    return score


def evaluate_vs_random(
    model_path,
    n_games=50,
    agent_color_mode="side-to-move",
    max_steps=100,
    success_material_advantage=3.0,
):
    model = MaskablePPO.load(str(model_path))
    env = ChessEnv(max_steps=max_steps)

    wins = 0
    losses = 0
    draws = 0
    truncated_games = 0
    agent_promotion_games = 0
    opponent_promotion_games = 0
    agent_promotion_moves = 0
    opponent_promotion_moves = 0
    material_advantage_games = 0
    endgame_successes = 0
    total_reward = 0.0
    total_material_advantage = 0.0

    for _ in range(n_games):
        obs, _ = env.reset()
        agent_color = choose_agent_color(agent_color_mode, env.board.turn)
        done = False
        truncated = False
        episode_reward = 0.0
        agent_promoted = False
        opponent_promoted = False

        while not (done or truncated):
            moving_color = env.board.turn

            if moving_color == agent_color:
                action_masks = env.action_masks()
                action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
                move = action_index_to_move(int(action))
            else:
                move = random.choice(list(env.board.legal_moves))
                action = move_to_action_index(move)

            if move is not None and move.promotion:
                if moving_color == agent_color:
                    agent_promoted = True
                    agent_promotion_moves += 1
                else:
                    opponent_promoted = True
                    opponent_promotion_moves += 1

            obs, reward, done, truncated, _ = env.step(action)
            episode_reward += reward if moving_color == agent_color else -reward

        result = env.board.result() if env.board.is_game_over() else None
        agent_won = (result == "1-0" and agent_color == chess.WHITE) or (
            result == "0-1" and agent_color == chess.BLACK
        )
        agent_lost = (result == "0-1" and agent_color == chess.WHITE) or (
            result == "1-0" and agent_color == chess.BLACK
        )

        if agent_won:
            wins += 1
        elif agent_lost:
            losses += 1
        else:
            draws += 1

        if truncated:
            truncated_games += 1
        if agent_promoted:
            agent_promotion_games += 1
        if opponent_promoted:
            opponent_promotion_games += 1

        final_material_advantage = material_advantage(env.board, agent_color)
        total_material_advantage += final_material_advantage
        has_material_advantage = final_material_advantage >= success_material_advantage
        if has_material_advantage:
            material_advantage_games += 1

        if agent_won or agent_promoted or has_material_advantage:
            endgame_successes += 1

        total_reward += episode_reward

    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "truncated_games": truncated_games,
        "agent_promotion_games": agent_promotion_games,
        "opponent_promotion_games": opponent_promotion_games,
        "agent_promotion_moves": agent_promotion_moves,
        "opponent_promotion_moves": opponent_promotion_moves,
        "material_advantage_games": material_advantage_games,
        "endgame_successes": endgame_successes,
        "winrate": wins / n_games if n_games > 0 else 0.0,
        "promotion_rate": agent_promotion_games / n_games if n_games > 0 else 0.0,
        "material_advantage_rate": material_advantage_games / n_games if n_games > 0 else 0.0,
        "endgame_success_rate": endgame_successes / n_games if n_games > 0 else 0.0,
        "avg_reward": total_reward / n_games if n_games > 0 else 0.0,
        "avg_material_advantage": total_material_advantage / n_games if n_games > 0 else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate a MaskablePPO chess agent against random legal moves.")
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--success-material-advantage", type=float, default=3.0)
    parser.add_argument(
        "--agent-color",
        choices=["side-to-move", "white", "black", "random"],
        default="side-to-move",
        help="Which color the agent should play in each game.",
    )
    parser.add_argument("--output", type=Path, default=Path("evaluation_vs_random.txt"))
    parser.add_argument("--csv-output", type=Path, default=Path("evaluation_vs_random.csv"))
    args = parser.parse_args()

    results = evaluate_vs_random(
        args.model_path,
        args.games,
        args.agent_color,
        args.max_steps,
        args.success_material_advantage,
    )
    report = (
        f"\nWyniki ewaluacji vs random ({args.model_path}):\n"
        f"Liczba gier: {args.games}\n"
        f"Kolor agenta: {args.agent_color}\n"
        f"Limit polruchow: {args.max_steps}\n"
        f"Prog przewagi materialu: {args.success_material_advantage:.1f}\n"
        f"Wygrane: {results['wins']}\n"
        f"Porazki: {results['losses']}\n"
        f"Remisy: {results['draws']}\n"
        f"Partie uciete limitem: {results['truncated_games']}\n"
        f"Winrate: {results['winrate']:.2f}\n"
        f"Partie z promocja agenta: {results['agent_promotion_games']}\n"
        f"Partie z promocja randoma: {results['opponent_promotion_games']}\n"
        f"Ruchy promocyjne agenta: {results['agent_promotion_moves']}\n"
        f"Ruchy promocyjne randoma: {results['opponent_promotion_moves']}\n"
        f"Promotion rate: {results['promotion_rate']:.2f}\n"
        f"Partie z przewaga materialu agenta: {results['material_advantage_games']}\n"
        f"Material advantage rate: {results['material_advantage_rate']:.2f}\n"
        f"Sukces koncowkowy: {results['endgame_successes']}\n"
        f"Endgame success rate: {results['endgame_success_rate']:.2f}\n"
        f"Srednia przewaga materialu: {results['avg_material_advantage']:.2f}\n"
        f"Sredni reward: {results['avg_reward']:.2f}\n"
        f"{'-' * 30}\n"
    )

    print(report)
    with args.output.open("a", encoding="utf-8") as f:
        f.write(report)
    print(f"Raport zostal zapisany w {args.output}")

    csv_fields = [
        "model_path",
        "games",
        "agent_color",
        "max_steps",
        "success_material_advantage",
        "wins",
        "losses",
        "draws",
        "truncated_games",
        "winrate",
        "agent_promotion_games",
        "opponent_promotion_games",
        "agent_promotion_moves",
        "opponent_promotion_moves",
        "promotion_rate",
        "material_advantage_games",
        "material_advantage_rate",
        "endgame_successes",
        "endgame_success_rate",
        "avg_material_advantage",
        "avg_reward",
    ]
    csv_row = {
        "model_path": str(args.model_path),
        "games": args.games,
        "agent_color": args.agent_color,
        "max_steps": args.max_steps,
        "success_material_advantage": args.success_material_advantage,
        **results,
    }
    write_header = not args.csv_output.exists()
    with args.csv_output.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        if write_header:
            writer.writeheader()
        writer.writerow({field: csv_row[field] for field in csv_fields})
    print(f"Wiersz CSV zostal zapisany w {args.csv_output}")


if __name__ == "__main__":
    main()

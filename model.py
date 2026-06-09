import argparse
from pathlib import Path

import matplotlib
import torch
from torch.distributions import Distribution
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from backend.env_ppo import ChessEnv
from backend.gnn_features import ChessGraphFeaturesExtractor


matplotlib.use("Agg")
import matplotlib.pyplot as plt

Distribution.set_default_validate_args(False)

DEFAULT_MODEL_PATH = Path("backend") / "ppo_chess_model_tuned"
DEFAULT_PROGRESS_CSV = Path("training_progress.csv")
DEFAULT_PROGRESS_PLOT = Path("training_progress.png")


def make_env():
    return ChessEnv()


def evaluate_trained_model(model, n_games=50):
    env = ChessEnv()
    wins, losses, draws = 0, 0, 0
    total_reward = 0.0

    for _ in range(n_games):
        obs, _ = env.reset()
        agent_color = env.board.turn
        done = False
        truncated = False
        episode_reward = 0.0

        while not (done or truncated):
            action_masks = env.action_masks()
            action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
            obs, reward, done, truncated, _ = env.step(action)
            episode_reward += reward

        result = env.board.result() if env.board.is_game_over() else None
        agent_won = (result == "1-0" and agent_color) or (result == "0-1" and not agent_color)
        agent_lost = (result == "0-1" and agent_color) or (result == "1-0" and not agent_color)

        if agent_won:
            wins += 1
        elif agent_lost:
            losses += 1
        else:
            draws += 1

        total_reward += episode_reward

    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "winrate": wins / n_games if n_games > 0 else 0,
        "avg_reward": total_reward / n_games if n_games > 0 else 0,
    }


def save_training_progress(history, csv_path=DEFAULT_PROGRESS_CSV, plot_path=DEFAULT_PROGRESS_PLOT):
    csv_path = Path(csv_path)
    plot_path = Path(plot_path)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("timesteps,wins,losses,draws,winrate,avg_reward\n")
        for row in history:
            f.write(
                f"{row['timesteps']},{row['wins']},{row['losses']},{row['draws']},"
                f"{row['winrate']:.6f},{row['avg_reward']:.6f}\n"
            )

    if not history:
        return

    timesteps = [row["timesteps"] for row in history]
    winrates = [row["winrate"] for row in history]
    avg_rewards = [row["avg_reward"] for row in history]

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(timesteps, winrates, marker="o", label="Winrate")
    plt.plot(timesteps, avg_rewards, marker="s", label="Sredni reward")
    plt.xlabel("Kroki treningu")
    plt.ylabel("Wartosc")
    plt.title("Postep uczenia PPO")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()


class TrainingProgressCallback(BaseCallback):
    def __init__(
        self,
        eval_freq=100_000,
        eval_games=20,
        csv_path=DEFAULT_PROGRESS_CSV,
        plot_path=DEFAULT_PROGRESS_PLOT,
    ):
        super().__init__()
        self.eval_freq = eval_freq
        self.eval_games = eval_games
        self.csv_path = csv_path
        self.plot_path = plot_path
        self.history = []
        self.last_eval_timestep = 0

    def _on_step(self):
        if self.num_timesteps - self.last_eval_timestep < self.eval_freq:
            return True

        self.last_eval_timestep = self.num_timesteps
        results = evaluate_trained_model(self.model, n_games=self.eval_games)
        row = {"timesteps": self.num_timesteps, **results}
        self.history.append(row)
        save_training_progress(self.history, self.csv_path, self.plot_path)

        print(
            f"\n[EVAL] kroki={self.num_timesteps} "
            f"winrate={results['winrate']:.2f} "
            f"wins={results['wins']} losses={results['losses']} draws={results['draws']} "
            f"avg_reward={results['avg_reward']:.2f}\n"
        )
        return True


def train(
    total_timesteps=2_000_000,
    n_envs=4,
    model_path=DEFAULT_MODEL_PATH,
    eval_freq=100_000,
    eval_games=20,
    progress_csv=DEFAULT_PROGRESS_CSV,
    progress_plot=DEFAULT_PROGRESS_PLOT,
):
    env = DummyVecEnv([make_env for _ in range(n_envs)])

    model = MaskablePPO(
        policy=MaskableActorCriticPolicy,
        env=env,
        verbose=1,
        policy_kwargs={
            "features_extractor_class": ChessGraphFeaturesExtractor,
            "features_extractor_kwargs": {
                "features_dim": 256,
                "hidden_dim": 128,
                "num_layers": 3,
            },
            "net_arch": {
                "pi": [128],
                "vf": [128],
            },
        },
        learning_rate=0.0001473730904598708,
        n_steps=4096,
        batch_size=64,
        gamma=0.9534792566772458,
        gae_lambda=0.9487839610636086,
        ent_coef=0.0010299955703915152,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    callback = TrainingProgressCallback(
        eval_freq=eval_freq,
        eval_games=eval_games,
        csv_path=progress_csv,
        plot_path=progress_plot,
    )

    model.learn(total_timesteps=total_timesteps, callback=callback)
    model.save(str(model_path))
    print(f"Model zapisany jako {model_path}")
    print(f"Wykres postepu zapisany jako {progress_plot}")
    print(f"Dane postepu zapisane jako {progress_csv}")


def evaluate(model_path=DEFAULT_MODEL_PATH, n_games=50):
    try:
        model = MaskablePPO.load(str(model_path))
    except FileNotFoundError:
        print(f"Blad: Nie znaleziono pliku {model_path}. Najpierw wytrenuj model.")
        return

    print(f"Rozpoczynam ewaluacje na dystansie {n_games} gier...")
    results = evaluate_trained_model(model, n_games=n_games)
    report = (
        f"\nWyniki ewaluacji ({model_path}):\n"
        f"Liczba gier: {n_games}\n"
        f"Wygrane: {results['wins']}\n"
        f"Porazki: {results['losses']}\n"
        f"Remisy: {results['draws']}\n"
        f"Winrate: {results['winrate']:.2f}\n"
        f"Sredni reward: {results['avg_reward']:.2f}\n"
        f"{'-' * 30}\n"
    )

    print(report)
    with open("evaluation_results.txt", "a", encoding="utf-8") as f:
        f.write(report)
    print("Raport zostal zapisany w evaluation_results.txt")


def play_demo(model_path=DEFAULT_MODEL_PATH):
    env = ChessEnv()
    try:
        model = MaskablePPO.load(str(model_path))
    except FileNotFoundError:
        print(f"Blad: Nie znaleziono pliku {model_path}.")
        return

    obs, _ = env.reset()
    done = False
    truncated = False

    print("\nDemo gry agenta:\n")
    while not (done or truncated):
        print("-" * 20)
        print(env.board)
        action_masks = env.action_masks()
        action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
        obs, reward, done, truncated, _ = env.step(action)

    print("\nKoniec gry!")
    print(env.board)
    print(f"Ostateczny wynik reward: {reward}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPO Chess Agent - koncowki")
    parser.add_argument(
        "--mode",
        type=str,
        default="train",
        choices=["train", "eval", "play"],
        help="Tryb pracy: train, eval albo play",
    )
    parser.add_argument("--timesteps", type=int, default=2_000_000)
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--eval-freq", type=int, default=100_000)
    parser.add_argument("--eval-games", type=int, default=20)
    parser.add_argument("--progress-csv", type=Path, default=DEFAULT_PROGRESS_CSV)
    parser.add_argument("--progress-plot", type=Path, default=DEFAULT_PROGRESS_PLOT)

    args = parser.parse_args()

    if args.mode == "train":
        train(
            total_timesteps=args.timesteps,
            n_envs=args.n_envs,
            model_path=args.model_path,
            eval_freq=args.eval_freq,
            eval_games=args.eval_games,
            progress_csv=args.progress_csv,
            progress_plot=args.progress_plot,
        )
    elif args.mode == "eval":
        evaluate(model_path=args.model_path, n_games=args.games)
    elif args.mode == "play":
        play_demo(model_path=args.model_path)

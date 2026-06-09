import argparse
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np
import optuna
import torch

from torch.distributions import Distribution
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.callbacks import CallbackList
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.logger import configure
from stable_baselines3.common.vec_env import DummyVecEnv

from backend.env_ppo import ChessEnv
from backend.gnn_features import ChessGraphFeaturesExtractor


matplotlib.use("Agg")
import matplotlib.pyplot as plt

Distribution.set_default_validate_args(False)

DEFAULT_STUDY_NAME = "ppo_chess_gnn_tuning"
DEFAULT_STORAGE = "sqlite:///optuna_chess_tuning.db"
DEFAULT_MODEL_PATH = Path("backend") / "ppo_chess_model_tuned"
DEFAULT_LOG_DIR = Path("tuning_logs") / "gnn_final_training"
DEFAULT_OUTPUT_DIR = Path("colab_outputs") / "gnn_tuning"


def make_env():
    return ChessEnv()


def sqlite_storage_for_path(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def sample_legal_action(env):
    legal_actions = np.flatnonzero(env.action_masks())
    if len(legal_actions) == 0:
        return env.action_space.sample()
    return int(np.random.choice(legal_actions))


def evaluate_model_vs_random(model, n_games=50):
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
            if env.board.turn == agent_color:
                action, _ = model.predict(
                    obs,
                    action_masks=env.action_masks(),
                    deterministic=True,
                )
            else:
                action = sample_legal_action(env)

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


def build_model(params, verbose=0):
    env = DummyVecEnv([make_env for _ in range(4)])
    return MaskablePPO(
        policy=MaskableActorCriticPolicy,
        env=env,
        verbose=verbose,
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
        learning_rate=params["learning_rate"],
        n_steps=params["n_steps"],
        batch_size=params["batch_size"],
        gamma=params["gamma"],
        gae_lambda=params["gae_lambda"],
        ent_coef=params["ent_coef"],
        device="cuda" if torch.cuda.is_available() else "cpu",
    )


def objective(trial, train_timesteps, eval_games):
    params = {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 5e-4, log=True),
        "gamma": trial.suggest_float("gamma", 0.95, 0.999),
        "gae_lambda": trial.suggest_float("gae_lambda", 0.85, 0.99),
        "ent_coef": trial.suggest_float("ent_coef", 0.001, 0.05, log=True),
        "n_steps": trial.suggest_categorical("n_steps", [512, 1024, 2048, 4096]),
        "batch_size": trial.suggest_categorical("batch_size", [64, 128, 256, 512]),
    }

    model = build_model(params)
    model.learn(total_timesteps=train_timesteps)

    results = evaluate_model_vs_random(model, n_games=eval_games)
    trial.set_user_attr("wins", results["wins"])
    trial.set_user_attr("losses", results["losses"])
    trial.set_user_attr("draws", results["draws"])

    return results["winrate"]


def write_eval_history(history, csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("timesteps,wins,losses,draws,winrate,avg_reward\n")
        for row in history:
            f.write(
                f"{row['timesteps']},{row['wins']},{row['losses']},{row['draws']},"
                f"{row['winrate']:.6f},{row['avg_reward']:.6f}\n"
            )


class FinalTrainingEvalCallback(BaseCallback):
    def __init__(self, eval_freq, eval_games, eval_csv_path):
        super().__init__()
        self.eval_freq = eval_freq
        self.eval_games = eval_games
        self.eval_csv_path = Path(eval_csv_path)
        self.history = []
        self.last_eval_timestep = 0

    def _on_step(self):
        if self.num_timesteps - self.last_eval_timestep < self.eval_freq:
            return True

        self.last_eval_timestep = self.num_timesteps
        results = evaluate_model_vs_random(self.model, n_games=self.eval_games)
        row = {"timesteps": self.num_timesteps, **results}
        self.history.append(row)
        write_eval_history(self.history, self.eval_csv_path)

        print(
            f"\n[FINAL EVAL] kroki={self.num_timesteps} "
            f"winrate={results['winrate']:.2f} "
            f"wins={results['wins']} losses={results['losses']} draws={results['draws']} "
            f"avg_reward={results['avg_reward']:.2f}\n"
        )
        return True


def read_numeric_csv(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return []

    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if value is None or value == "":
                    continue
                try:
                    parsed[key] = float(value)
                except ValueError:
                    pass
            if parsed:
                rows.append(parsed)
    return rows


def plot_eval_history(eval_csv_path, output_path):
    rows = read_numeric_csv(eval_csv_path)
    if not rows:
        return

    timesteps = [row["timesteps"] for row in rows]
    winrates = [row["winrate"] for row in rows]
    avg_rewards = [row["avg_reward"] for row in rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(timesteps, winrates, marker="o", label="Winrate vs random")
    plt.plot(timesteps, avg_rewards, marker="s", label="Sredni reward")
    plt.xlabel("Kroki treningu")
    plt.ylabel("Wartosc")
    plt.title("Finalny trening GNN PPO - ewaluacja")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_loss_history(progress_csv_path, output_path):
    rows = read_numeric_csv(progress_csv_path)
    rows = [row for row in rows if "time/total_timesteps" in row]
    if not rows:
        return

    series = [
        ("train/loss", "Loss"),
        ("train/policy_gradient_loss", "Policy gradient loss"),
        ("train/value_loss", "Value loss"),
        ("train/entropy_loss", "Entropy loss"),
        ("train/approx_kl", "Approx KL"),
    ]
    available = [(key, label) for key, label in series if any(key in row for row in rows)]
    if not available:
        return

    timesteps = [row.get("time/total_timesteps", 0) for row in rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(11, 6))
    for key, label in available:
        values = [row.get(key, np.nan) for row in rows]
        plt.plot(timesteps, values, marker="o", label=label)

    plt.xlabel("Kroki treningu")
    plt.ylabel("Wartosc")
    plt.title("Finalny trening GNN PPO - funkcje straty i metryki PPO")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_best_params(params, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)


def save_study_trials(study, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("number,state,value,learning_rate,gamma,gae_lambda,ent_coef,n_steps,batch_size,wins,losses,draws\n")
        for trial in study.trials:
            params = trial.params
            attrs = trial.user_attrs
            f.write(
                f"{trial.number},{trial.state.name},{trial.value},"
                f"{params.get('learning_rate','')},{params.get('gamma','')},"
                f"{params.get('gae_lambda','')},{params.get('ent_coef','')},"
                f"{params.get('n_steps','')},{params.get('batch_size','')},"
                f"{attrs.get('wins','')},{attrs.get('losses','')},{attrs.get('draws','')}\n"
            )


def train_best_model(
    params,
    total_timesteps,
    model_path,
    log_dir,
    eval_freq,
    eval_games,
    checkpoint_freq,
):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)

    eval_csv_path = log_dir / "final_eval_progress.csv"
    eval_plot_path = log_dir / "final_eval_progress.png"
    loss_plot_path = log_dir / "final_losses.png"
    progress_csv_path = log_dir / "progress.csv"
    checkpoint_dir = log_dir / "checkpoints"

    model = build_model(params, verbose=1)
    model.set_logger(configure(str(log_dir), ["stdout", "csv"]))

    callback = FinalTrainingEvalCallback(
        eval_freq=eval_freq,
        eval_games=eval_games,
        eval_csv_path=eval_csv_path,
    )
    callbacks = [callback]

    if checkpoint_freq > 0:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        callbacks.append(
            CheckpointCallback(
                save_freq=checkpoint_freq,
                save_path=str(checkpoint_dir),
                name_prefix="ppo_chess_gnn_checkpoint",
            )
        )

    model.learn(total_timesteps=total_timesteps, callback=CallbackList(callbacks))
    model.save(str(model_path))
    plot_eval_history(eval_csv_path, eval_plot_path)
    plot_loss_history(progress_csv_path, loss_plot_path)

    print(f"Najlepszy model zapisany jako {model_path}")
    print(f"Dane treningu zapisane w {log_dir}")
    print(f"Wykres ewaluacji: {eval_plot_path}")
    print(f"Wykres loss/metryk PPO: {loss_plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optuna tuning dla MaskablePPO Chess Agent")
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--timesteps", type=int, default=150_000)
    parser.add_argument("--eval-games", type=int, default=50)
    parser.add_argument("--final-timesteps", type=int, default=1_000_000)
    parser.add_argument("--final-eval-freq", type=int, default=100_000)
    parser.add_argument("--final-eval-games", type=int, default=50)
    parser.add_argument("--checkpoint-freq", type=int, default=100_000)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--storage", type=str, default=DEFAULT_STORAGE)
    parser.add_argument("--study-name", type=str, default=DEFAULT_STUDY_NAME)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument(
        "--skip-final-train",
        action="store_true",
        help="Tylko stroi parametry, bez finalnego treningu najlepszego modelu.",
    )
    args = parser.parse_args()

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        args.storage = sqlite_storage_for_path(args.output_dir / "optuna_chess_gnn_tuning.db")
        args.model_path = args.output_dir / "ppo_chess_model_tuned"
        args.log_dir = args.output_dir / "logs"

    if torch.cuda.is_available():
        print("GPU jest dostepne. Uzywanie GPU do treningu.")
    else:
        print("GPU nie jest dostepne. Uzywanie CPU do treningu.")

    study = optuna.create_study(
        direction="maximize",
        study_name=args.study_name,
        storage=args.storage,
        load_if_exists=True,
    )
    study.optimize(
        lambda trial: objective(trial, args.timesteps, args.eval_games),
        n_trials=args.trials,
        catch=(ValueError,),
    )

    print("Najlepszy wynik:", study.best_value)
    print("Najlepsze parametry:", study.best_params)
    save_best_params(study.best_params, Path(args.log_dir) / "best_params.json")
    save_study_trials(study, Path(args.log_dir) / "optuna_trials.csv")

    if not args.skip_final_train:
        train_best_model(
            study.best_params,
            args.final_timesteps,
            args.model_path,
            args.log_dir,
            args.final_eval_freq,
            args.final_eval_games,
            args.checkpoint_freq,
        )

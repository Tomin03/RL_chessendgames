import argparse
from pathlib import Path

import numpy as np
import optuna
import torch

from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.vec_env import DummyVecEnv

from backend.env_ppo import ChessEnv


DEFAULT_STUDY_NAME = "ppo_chess_tuning"
DEFAULT_STORAGE = "sqlite:///optuna_chess_tuning.db"
DEFAULT_MODEL_PATH = Path("backend") / "ppo_chess_model_tuned"


def make_env():
    return ChessEnv()


def sample_legal_action(env):
    legal_actions = np.flatnonzero(env.action_masks())
    if len(legal_actions) == 0:
        return env.action_space.sample()
    return int(np.random.choice(legal_actions))


def evaluate_model_vs_random(model, n_games=50):
    env = ChessEnv()
    wins, losses, draws = 0, 0, 0

    for _ in range(n_games):
        obs, _ = env.reset()
        agent_color = env.board.turn
        done = False
        truncated = False

        while not (done or truncated):
            if env.board.turn == agent_color:
                action, _ = model.predict(
                    obs,
                    action_masks=env.action_masks(),
                    deterministic=True,
                )
            else:
                action = sample_legal_action(env)

            obs, _, done, truncated, _ = env.step(action)

        result = env.board.result() if env.board.is_game_over() else None
        agent_won = (result == "1-0" and agent_color) or (result == "0-1" and not agent_color)
        agent_lost = (result == "0-1" and agent_color) or (result == "1-0" and not agent_color)

        if agent_won:
            wins += 1
        elif agent_lost:
            losses += 1
        else:
            draws += 1

    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "winrate": wins / n_games if n_games > 0 else 0,
    }


def build_model(params, verbose=0):
    env = DummyVecEnv([make_env for _ in range(4)])
    return MaskablePPO(
        policy=MaskableActorCriticPolicy,
        env=env,
        verbose=verbose,
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
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
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


def train_best_model(params, total_timesteps, model_path):
    model = build_model(params, verbose=1)
    model.learn(total_timesteps=total_timesteps)
    model.save(str(model_path))
    print(f"Najlepszy model zapisany jako {model_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optuna tuning dla MaskablePPO Chess Agent")
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--timesteps", type=int, default=150_000)
    parser.add_argument("--eval-games", type=int, default=50)
    parser.add_argument("--final-timesteps", type=int, default=1_000_000)
    parser.add_argument("--storage", type=str, default=DEFAULT_STORAGE)
    parser.add_argument("--study-name", type=str, default=DEFAULT_STUDY_NAME)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--skip-final-train",
        action="store_true",
        help="Tylko stroi parametry, bez finalnego treningu najlepszego modelu.",
    )
    args = parser.parse_args()

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
    )

    print("Najlepszy wynik:", study.best_value)
    print("Najlepsze parametry:", study.best_params)

    if not args.skip_final_train:
        train_best_model(study.best_params, args.final_timesteps, args.model_path)

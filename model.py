import argparse
from pathlib import Path

import torch
from torch.distributions import Distribution
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.vec_env import DummyVecEnv

from backend.env_ppo import ChessEnv


Distribution.set_default_validate_args(False)

DEFAULT_MODEL_PATH = Path("backend") / "ppo_chess_model"


def make_env():
    return ChessEnv()


def train(total_timesteps=2_000_000, n_envs=4, model_path=DEFAULT_MODEL_PATH):
    env = DummyVecEnv([make_env for _ in range(n_envs)])

    model = MaskablePPO(
        policy=MaskableActorCriticPolicy,
        env=env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.02,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    model.learn(total_timesteps=total_timesteps)
    model.save(str(model_path))
    print(f"Model zapisany jako {model_path}")


def evaluate(model_path=DEFAULT_MODEL_PATH, n_games=50):
    env = ChessEnv()
    try:
        model = MaskablePPO.load(str(model_path))
    except FileNotFoundError:
        print(f"Blad: Nie znaleziono pliku {model_path}. Najpierw wytrenuj model.")
        return

    wins, losses, draws = 0, 0, 0
    print(f"Rozpoczynam ewaluacje na dystansie {n_games} gier...")

    for _ in range(n_games):
        obs, _ = env.reset()
        done = False
        truncated = False
        final_reward = 0

        while not (done or truncated):
            action_masks = env.action_masks()
            action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
            obs, reward, done, truncated, _ = env.step(action)
            final_reward = reward

        if final_reward >= 5:
            wins += 1
        elif final_reward <= -5:
            losses += 1
        else:
            draws += 1

    winrate = wins / n_games if n_games > 0 else 0
    report = (
        f"\nWyniki ewaluacji ({model_path}):\n"
        f"Liczba gier: {n_games}\n"
        f"Wygrane: {wins}\n"
        f"Porazki: {losses}\n"
        f"Remisy: {draws}\n"
        f"Winrate: {winrate:.2f}\n"
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

    args = parser.parse_args()

    if args.mode == "train":
        train(total_timesteps=args.timesteps, n_envs=args.n_envs, model_path=args.model_path)
    elif args.mode == "eval":
        evaluate(model_path=args.model_path, n_games=args.games)
    elif args.mode == "play":
        play_demo(model_path=args.model_path)

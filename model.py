from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.vec_env import DummyVecEnv
import torch
import numpy as np
import argparse
from env_ppo import ChessEnv

def make_env():
    return ChessEnv()

def train():
    env = DummyVecEnv([make_env])

    model = MaskablePPO(
        policy=MaskableActorCriticPolicy,
        env=env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.08, 
        device="cuda" if torch.cuda.is_available() else "cpu"
    )

    model.learn(total_timesteps=200_000)
    model.save("ppo_chess_model")
    print("Model zapisany jako ppo_chess_model")

def evaluate(model_path="ppo_chess_model", n_games=50):
    env = ChessEnv()
    try:
        model = MaskablePPO.load(model_path)
    except FileNotFoundError:
        print(f"❌ Błąd: Nie znaleziono pliku {model_path}. Najpierw wytrenuj model!")
        return

    wins, losses, draws = 0, 0, 0

    print(f"🧐 Rozpoczynam ewaluację na dystansie {n_games} gier...")

    for i in range(n_games):
        obs, _ = env.reset()
        done = False
        truncated = False
        final_reward = 0

        # Pętla pojedynczej partii
        while not (done or truncated):
            action_masks = env.action_masks()
            # deterministic=False sprawia, że agent nie zawsze gra idealnie,
            # co pozwala zaobserwować np. wchodzenie pod bicie.
            action, _ = model.predict(obs, action_masks=action_masks, deterministic=False)
            obs, reward, done, truncated, _ = env.step(action)
            final_reward = reward

        if final_reward >= 0.8:   # Wygrana (+1 plus ewentualne bonusy za bicia)
            wins += 1
        elif final_reward <= -0.8: # Porażka (-1)
            losses += 1
        else:
            draws += 1

    # Przygotowanie i wyświetlenie raportu
    winrate = wins / n_games if n_games > 0 else 0
    report = (
        f"\n📊 Wyniki ewaluacji ({model_path}):\n"
        f"Liczba gier: {n_games}\n"
        f"Wygrane: {wins}\n"
        f"Porażki: {losses}\n"
        f"Remisy: {draws}\n"
        f"Winrate: {winrate:.2f}\n"
        f"{'-'*30}\n"
    )

    print(report)

    with open("evaluation_results.txt", "a", encoding="utf-8") as f:
        f.write(report)
    print("✅ Raport został zapisany w evaluation_results.txt")

def play_demo(model_path="ppo_chess_model"):
    env = ChessEnv()
    try:
        model = MaskablePPO.load(model_path)
    except FileNotFoundError:
        print(f"❌ Błąd: Nie znaleziono pliku {model_path}!")
        return

    obs, _ = env.reset()
    done = False
    truncated = False

    print("\n♟️ Demo gry (Tryb Niedeterministyczny - wysoka entropia):\n")
    while not (done or truncated):
        print("-" * 20)
        print(env.board)
        action_masks = env.action_masks()

        action, _ = model.predict(
            obs,
            action_masks=action_masks,
            deterministic=False 
        )
        obs, reward, done, truncated, _ = env.step(action)

    print("\n🏁 Koniec gry!")
    print(env.board)
    print(f"Ostateczny wynik (reward): {reward}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPO Chess Agent - Końcówki")
    parser.add_argument("--mode", type=str, default="train",
                        choices=["train", "eval", "play"],
                        help="Tryb pracy: train (trenowanie), eval (statystyki), play (wizualizacja)")

    args = parser.parse_args()

    if args.mode == "train":
        train()
    elif args.mode == "eval":
        evaluate()
    elif args.mode == "play":
        play_demo()
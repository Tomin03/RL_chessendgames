import optuna
import torch

from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.vec_env import DummyVecEnv

from backend.env_ppo import ChessEnv


def make_env():
    return ChessEnv()


def evaluate_model(model, n_games=20):
    env = ChessEnv()
    wins = 0

    for _ in range(n_games):
        obs, _ = env.reset()
        done = False
        truncated = False
        final_reward = 0

        while not (done or truncated):
            action, _ = model.predict(
                obs,
                action_masks=env.action_masks(),
                deterministic=True,
            )
            obs, reward, done, truncated, _ = env.step(action)
            final_reward = reward

        if final_reward >= 5:
            wins += 1

    return wins / n_games


def objective(trial):
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
    gamma = trial.suggest_float("gamma", 0.95, 0.999)
    gae_lambda = trial.suggest_float("gae_lambda", 0.85, 0.99)
    ent_coef = trial.suggest_float("ent_coef", 0.001, 0.05, log=True)
    n_steps = trial.suggest_categorical("n_steps", [512, 1024, 2048, 4096])
    batch_size = trial.suggest_categorical("batch_size", [64, 128, 256, 512])

    env = DummyVecEnv([make_env for _ in range(4)])

    model = MaskablePPO(
        policy=MaskableActorCriticPolicy,
        env=env,
        verbose=0,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        gamma=gamma,
        gae_lambda=gae_lambda,
        ent_coef=ent_coef,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    model.learn(total_timesteps=150_000)

    return evaluate_model(model, n_games=20)


if __name__ == "__main__":
    if torch.cuda.is_available():
        print("GPU jest dostępne. Używanie GPU do treningu.")
    else:
        print("GPU nie jest dostępne. Używanie CPU do treningu.")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=30)

    print("Najlepszy wynik:", study.best_value)
    print("Najlepsze parametry:", study.best_params)
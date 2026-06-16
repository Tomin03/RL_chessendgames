import argparse
from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.logger import configure
from stable_baselines3.common.utils import get_schedule_fn
from stable_baselines3.common.vec_env import DummyVecEnv

from tune import make_env


def main():
    parser = argparse.ArgumentParser(description="Resume MaskablePPO training from a checkpoint.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--target-timesteps", type=int, default=3_000_000)
    parser.add_argument("--checkpoint-freq", type=int, default=100_000)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/resumed_training"))
    args = parser.parse_args()

    if not args.checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint}")

    output_dir = args.output_dir
    checkpoint_dir = output_dir / "checkpoints"
    log_dir = output_dir / "logs"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    env = DummyVecEnv([make_env for _ in range(4)])
    model = MaskablePPO.load(args.checkpoint, env=env, device="auto")

    # Rebuild schedules locally. Cloudpickled schedule functions from Colab can
    # bind incorrectly after moving the checkpoint from Linux to Windows.
    model.lr_schedule = get_schedule_fn(model.learning_rate)
    model.clip_range = get_schedule_fn(0.2)

    remaining_timesteps = args.target_timesteps - model.num_timesteps
    if remaining_timesteps <= 0:
        raise ValueError(
            f"Checkpoint already has {model.num_timesteps} timesteps, "
            f"target is {args.target_timesteps}."
        )

    model.set_logger(configure(str(log_dir), ["stdout", "csv"]))
    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.checkpoint_freq // env.num_envs, 1),
        save_path=str(checkpoint_dir),
        name_prefix="ppo_chess_gnn_checkpoint_resumed",
    )

    print(
        f"Resuming from {model.num_timesteps} to {args.target_timesteps} "
        f"timesteps ({remaining_timesteps} remaining)."
    )
    model.learn(
        total_timesteps=remaining_timesteps,
        callback=checkpoint_callback,
        reset_num_timesteps=False,
    )

    final_model = output_dir / "ppo_chess_gnn_final"
    model.save(str(final_model))
    print(f"Final model saved to {final_model}.zip")


if __name__ == "__main__":
    main()

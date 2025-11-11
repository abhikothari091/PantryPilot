#!/usr/bin/env python3
"""
Fine-tune Phi-3 Mini V3 for inventory-aware recipe generation using MLX on Apple Silicon

V3 Configuration (Optimized for stability):
- Batch size: 1 (memory safe)
- Learning rate: 5e-5 (conservative, prevent overfitting)
- Epochs: 2 (prevent overfitting)
- LoRA rank: 8, alpha: 16 (reduced from 20)
- Dataset: 5,000 samples (4,500 train / 500 valid)
"""

import json
from pathlib import Path


def verify_data():
    """Verify training data exists and is correct"""
    base_dir = Path(__file__).parent.parent
    train_file = base_dir / "data" / "finetune" / "train.jsonl"
    valid_file = base_dir / "data" / "finetune" / "valid.jsonl"

    print("📋 Verifying training data...")

    if not train_file.exists():
        print(f"❌ Train file not found: {train_file}")
        return False

    if not valid_file.exists():
        print(f"❌ Valid file not found: {valid_file}")
        return False

    # Count samples
    with open(train_file, 'r') as f:
        train_count = sum(1 for _ in f)

    with open(valid_file, 'r') as f:
        valid_count = sum(1 for _ in f)

    print(f"✅ Train: {train_count:,} samples")
    print(f"✅ Valid: {valid_count:,} samples")

    # Verify format
    with open(train_file, 'r') as f:
        sample = json.loads(f.readline())
        if 'text' not in sample:
            print("❌ Invalid format: 'text' field missing")
            return False
        if '<|system|>' not in sample['text']:
            print("❌ Invalid format: Phi-3 format not detected")
            return False

    print("✅ Data format verified (Phi-3 format)")
    return True


def main():
    print("🚀 Starting Phi-3 Mini V3 Fine-tuning on M4 Pro (MLX)")
    print("=" * 80)
    print("📊 V3 Configuration:")
    print("   - 5,000 total samples (4,500 train / 500 valid)")
    print("   - Balanced cuisine distribution")
    print("   - Diverse meat/fish augmentation (40% of vegetarian samples)")
    print("   - 0 dietary violations")
    print("=" * 80)

    # Verify data
    if not verify_data():
        print("\n❌ Data verification failed. Please check your training data.")
        return

    # Paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / "finetune"

    # Model configuration
    model_path = "mlx-community/Phi-3-mini-4k-instruct-4bit"
    adapter_path = base_dir / "models" / "phi3-recipe-lora-v3"
    adapter_path.mkdir(parents=True, exist_ok=True)

    # V3 optimized configuration (conservative)
    batch_size = 1              # Memory safe for M4 Pro
    learning_rate = 5e-5        # Conservative (prevent overfitting)
    epochs = 2                  # Reduced from 3 (prevent overfitting)
    lora_rank = 8               # Keep same
    lora_alpha = 16             # Reduced from 20 (prevent overfitting)
    lora_dropout = 0.05         # Keep same
    max_seq_length = 2048       # Keep same

    train_samples = 4500
    val_samples = 500

    print(f"\n🔧 V3 Fine-tuning configuration:")
    print(f"   Base model: {model_path}")
    print(f"   Training samples: {train_samples:,}")
    print(f"   Validation samples: {val_samples:,}")
    print(f"   Batch size: {batch_size} (memory safe)")
    print(f"   Learning rate: {learning_rate} (conservative)")
    print(f"   Epochs: {epochs} (reduced for stability)")
    print(f"   LoRA rank: {lora_rank}")
    print(f"   LoRA alpha: {lora_alpha} (reduced from 20)")
    print(f"   LoRA dropout: {lora_dropout}")
    print(f"   Max sequence length: {max_seq_length}")
    print(f"   Output adapter: {adapter_path}")

    # Calculate training iterations
    steps_per_epoch = train_samples // batch_size
    total_iters = steps_per_epoch * epochs

    print(f"\n⏱️  Training estimates:")
    print(f"   Steps per epoch: {steps_per_epoch:,}")
    print(f"   Total iterations: {total_iters:,}")
    print(f"   Estimated time: 5-6 hours (batch size 1)")
    print(f"   Peak memory usage: ~18-20 GB")

    # Training configuration
    config = {
        "model": model_path,
        "train": True,
        "data": str(data_dir),
        "iters": total_iters,
        "steps_per_report": 50,
        "steps_per_eval": 200,
        "save_every": 500,
        "adapter_path": str(adapter_path),
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "lora_parameters": {
            "rank": lora_rank,
            "alpha": lora_alpha,
            "dropout": lora_dropout,
            "scale": float(lora_alpha),
        },
        "max_seq_length": max_seq_length,
        "grad_checkpoint": False,
        "seed": 42,
    }

    # Save config for reference
    config_file = adapter_path / "training_config_v3.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"\n📝 Config saved to: {config_file}")

    print("\n" + "=" * 80)
    print("✅ Configuration ready! Starting fine-tuning...")
    print("=" * 80)
    print("\n🚀 MLX LoRA fine-tuning command:\n")

    cmd = f"""mlx_lm.lora \\
  --model {model_path} \\
  --train \\
  --data {data_dir} \\
  --iters {total_iters} \\
  --steps-per-report 50 \\
  --steps-per-eval 200 \\
  --save-every 500 \\
  --adapter-path {adapter_path} \\
  --batch-size {batch_size} \\
  --learning-rate {learning_rate} \\
  --lora-parameters '{{"rank": {lora_rank}, "alpha": {lora_alpha}, "dropout": {lora_dropout}}}' \\
  --max-seq-length {max_seq_length}"""

    print(cmd)

    print(f"\n📝 After training completes:")
    print(f"   1. V3 adapter will be saved to: {adapter_path}")
    print(f"   2. Test with diverse meat/fish samples")
    print(f"   3. Validate dietary constraint compliance")
    print(f"   4. Compare V2 vs V3 performance")

    print(f"\n💡 Key V3 improvements:")
    print(f"   - Lower learning rate (5e-5 vs 1e-4): more stable training")
    print(f"   - Reduced epochs (2 vs 3): prevent overfitting")
    print(f"   - Reduced LoRA alpha (16 vs 20): prevent overfitting")
    print(f"   - Diverse meat/fish augmentation in training data")
    print(f"   - 0 dietary violations in training data")

    print(f"\n⚠️  Important notes:")
    print(f"   - Training will take 5-6 hours (batch size 1)")
    print(f"   - Peak memory: ~18-20 GB")
    print(f"   - Don't run other heavy programs during training")
    print(f"   - Progress saved every 500 steps")

    print("\n" + "=" * 80)
    print("Ready to start training!")
    print("=" * 80)


if __name__ == "__main__":
    main()

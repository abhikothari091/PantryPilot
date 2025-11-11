# Training Scripts

## Overview

This directory contains scripts and configurations for fine-tuning Phi-3 Mini V3 on Apple Silicon using MLX.

## Files

### finetune_mlx_v3.py
Pre-flight check script that:
- Verifies training data
- Shows configuration
- Estimates training time
- Displays MLX command

**Usage**:
```bash
python finetune_mlx_v3.py
```

### lora_config_v3.yaml
MLX LoRA configuration file with V3 hyperparameters:
- Learning rate: 5e-5 (conservative)
- Batch size: 1 (memory safe)
- Epochs: 2 (prevent overfitting)
- LoRA alpha: 16 (reduced from 20)

**Usage**:
```bash
mlx_lm.lora --config lora_config_v3.yaml
```

### colab_finetune_phi3_v3_fixed.ipynb
Jupyter notebook for Google Colab training (T4 GPU).
**Note**: Kept for reference, but MLX (Mac) is recommended due to Colab compatibility issues.

## Quick Start

```bash
# 1. Verify setup
python finetune_mlx_v3.py

# 2. Start training
mlx_lm.lora --config lora_config_v3.yaml
```

## Expected Time
~5-6 hours on Mac M4 Pro

## Documentation
See [../docs/TRAINING_GUIDE.md](../docs/TRAINING_GUIDE.md) for complete training instructions.

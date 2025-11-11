# Training Guide: Phi-3 Mini V3 Fine-tuning

## Overview

This guide covers fine-tuning Phi-3 Mini 4K Instruct on Apple Silicon (M4 Pro) using MLX framework with conservative hyperparameters to prevent overfitting.

**Platform**: Mac M4 Pro + MLX
**Model**: Phi-3-mini-4k-instruct-4bit (3.8B parameters)
**Framework**: MLX (Apple Silicon optimized)
**Training Time**: ~5-6 hours
**Peak Memory**: ~15 GB

---

## Prerequisites

### Hardware Requirements
- Mac with Apple Silicon (M1/M2/M3/M4)
- Minimum 16 GB unified memory (24 GB recommended)
- ~20 GB free disk space

### Software Requirements
```bash
# Python 3.10+
python --version

# MLX and MLX-LM
pip install mlx mlx-lm

# Verify installation
python -c "import mlx; print(mlx.__version__)"
```

---

## Configuration Overview

### V3 Hyperparameters (Conservative)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Model** | mlx-community/Phi-3-mini-4k-instruct-4bit | 4-bit quantized for efficiency |
| **Learning Rate** | 5e-5 | Lower than V2 (1e-4) to prevent overfitting |
| **Epochs** | 2 | Reduced from 3 to prevent overfitting |
| **Batch Size** | 1 | Memory safe for M4 Pro |
| **LoRA Rank** | 8 | Standard rank for Phi-3 |
| **LoRA Alpha** | 16 | Reduced from 20 to decrease learning magnitude |
| **LoRA Dropout** | 0.05 | Standard dropout rate |
| **Max Seq Length** | 2048 | Sufficient for recipe generation |
| **Gradient Checkpoint** | False | Disabled for speed |

### Training Schedule
- **Total iterations**: 9,000 (4,500 per epoch × 2 epochs)
- **Steps per report**: 50 (progress updates)
- **Steps per eval**: 200 (validation checks)
- **Save every**: 500 (checkpoint saves)

---

## Training Configuration File

**File**: `training/lora_config_v3.yaml`

```yaml
# Model
model: "mlx-community/Phi-3-mini-4k-instruct-4bit"

# Training
train: true
data: "data/finetune"
iters: 9000
batch_size: 1
learning_rate: 5e-05

# LoRA Configuration
lora_parameters:
  rank: 8
  alpha: 16
  dropout: 0.05
  scale: 16.0

# Training schedule
steps_per_report: 50
steps_per_eval: 200
save_every: 500

# Model parameters
max_seq_length: 2048
adapter_path: "models/phi3-recipe-lora-v3"

# Advanced
grad_checkpoint: false
seed: 42
```

---

## Step-by-Step Training

### Step 1: Verify Data

```bash
cd data_pipeline

# Check data files exist
ls -lh data/finetune/train.jsonl data/finetune/valid.jsonl

# Expected output:
# -rw-r--r--  13M  train.jsonl
# -rw-r--r--  1.5M valid.jsonl

# Count samples
wc -l data/finetune/*.jsonl
# Expected: 4500 train.jsonl, 500 valid.jsonl
```

### Step 2: Run Pre-flight Check

```bash
cd training
python finetune_mlx_v3.py
```

**Expected Output**:
```
🚀 Starting Phi-3 Mini V3 Fine-tuning on M4 Pro (MLX)
================================================================================
📊 V3 Configuration:
   - 5,000 total samples (4,500 train / 500 valid)
   ...
📋 Verifying training data...
✅ Train: 4,500 samples
✅ Valid: 500 samples
✅ Data format verified (Phi-3 format)

🔧 V3 Fine-tuning configuration:
   Base model: mlx-community/Phi-3-mini-4k-instruct-4bit
   ...
   Batch size: 1 (memory safe)
   Learning rate: 5e-05 (conservative)
   Epochs: 2 (reduced for stability)
   ...

⏱️  Training estimates:
   Steps per epoch: 4,500
   Total iterations: 9,000
   Estimated time: 5-6 hours (batch size 1)
   Peak memory usage: ~18-20 GB

✅ Configuration ready! Starting fine-tuning...
```

### Step 3: Start Training

```bash
mlx_lm.lora --config lora_config_v3.yaml
```

**Initial Output**:
```
Loading configuration file lora_config_v3.yaml
Loading pretrained model
Loading datasets
Training
Trainable parameters: 0.165% (6.291M/3821.080M)
Starting training..., iters: 9000
Iter 1: Val loss 1.443, Val took 28.065s
```

### Step 4: Monitor Training

Training runs in foreground. Open new terminal to monitor:

```bash
# Check memory usage
top -pid $(pgrep -f mlx_lm)

# Expected:
# MEM: ~10-15 GB (will increase during training)
```

**Training Progress Output**:
```
Iter 50: Train loss 0.783, Learning Rate 5.000e-05, It/sec 0.509, Tokens/sec 405.267
Iter 100: Train loss 0.683, Learning Rate 5.000e-05, It/sec 0.444, Tokens/sec 340.995
Iter 150: Train loss 0.666, Learning Rate 5.000e-05, It/sec 0.440, Tokens/sec 354.945
Iter 200: Val loss 0.738, Val took 36.320s
Iter 200: Train loss 0.644, Learning Rate 5.000e-05, It/sec 0.429, Tokens/sec 360.625
...
Iter 500: Saved adapter weights to models/phi3-recipe-lora-v3/adapters.safetensors
```

---

## Understanding Training Metrics

### Key Metrics

**Train Loss**:
- Initial: ~0.78-0.80
- Target: < 0.60 by end of training
- Trend: Should decrease steadily

**Validation Loss**:
- Initial: ~1.44
- Target: < 0.65 by end
- Checked every 200 steps

**Speed** (It/sec):
- Expected: 0.4-0.5 it/sec (batch size 1)
- Lower = slower, higher = faster
- Depends on sequence length

**Tokens/sec**:
- Expected: 340-400 tokens/sec
- Throughput measure

**Peak Memory**:
- Initial: ~10 GB
- During training: ~15 GB
- Should not exceed 20 GB

### Loss Curves

**Healthy Training**:
```
Epoch 1:
  Train: 0.78 → 0.65 → 0.60 (decreasing)
  Val:   0.74 → 0.68 → 0.65 (decreasing)

Epoch 2:
  Train: 0.58 → 0.55 → 0.52 (decreasing)
  Val:   0.63 → 0.62 → 0.61 (stable or slight decrease)
```

**Overfitting Signs** (should NOT happen with V3 config):
```
Train: 0.78 → 0.45 → 0.30 (too fast decrease)
Val:   0.74 → 0.75 → 0.80 (increasing)
```

---

## Checkpoints and Resuming

### Automatic Checkpoints

Checkpoints saved every 500 steps:
```
models/phi3-recipe-lora-v3/
├── adapters.safetensors         # Latest checkpoint
├── 0000500_adapters.safetensors # Step 500
├── 0001000_adapters.safetensors # Step 1000
├── 0001500_adapters.safetensors # Step 1500
...
```

### Resuming Training

If training interrupted:
```bash
mlx_lm.lora \
  --config lora_config_v3.yaml \
  --resume-adapter-file models/phi3-recipe-lora-v3/0001500_adapters.safetensors
```

---

## Post-Training

### Step 1: Verify Adapter

```bash
ls -lh models/phi3-recipe-lora-v3/

# Expected files:
# adapters.safetensors (~24 MB)
# adapter_config.json
# training_config_v3.json
```

### Step 2: Test the Model

```python
from mlx_lm import load, generate

# Load base model + adapter
model, tokenizer = load(
    "mlx-community/Phi-3-mini-4k-instruct-4bit",
    adapter_path="models/phi3-recipe-lora-v3"
)

# Test prompt
test_prompt = """<|system|>
You are a creative recipe generator with access to the user's pantry inventory.

Available ingredients in pantry:
- tomato (vegetable)
- onion (vegetable)
- garlic (vegetable)
- chicken breast (meat) [FORBIDDEN for vegetarian]
- olive oil (oil)
- pasta (grain)
- salt (seasoning)
- pepper (seasoning)

User dietary preference: vegetarian

Instructions:
1. Based on the user's request, select appropriate ingredients from the available inventory
2. IMPORTANT: Respect dietary restrictions - do NOT select meat/fish for vegetarian recipes
3. Generate a complete, practical recipe with clear steps<|end|>
<|user|>
I want a healthy vegetarian dinner<|end|>
<|assistant|>
"""

# Generate
output = generate(
    model, tokenizer,
    prompt=test_prompt,
    max_tokens=512,
    temp=0.7
)

print(output)
```

**Expected Output** (should NOT include chicken breast):
```
Recipe: Tomato Basil Pasta

Selected ingredients from your pantry:
- pasta
- tomato
- onion
- garlic
- olive oil
- salt
- pepper

Instructions:
1. Boil pasta according to package directions
2. While pasta cooks, dice tomato, onion, and garlic
3. Sauté onion and garlic in olive oil until fragrant
4. Add diced tomato and simmer for 10 minutes
5. Season with salt and pepper
6. Toss with cooked pasta and serve<|end|>
```

### Step 3: Validation Test Cases

Create test cases for dietary constraints:

```python
test_cases = [
    {
        "name": "Vegetarian with chicken breast",
        "dietary": "vegetarian",
        "forbidden": ["chicken breast"],
        "allowed": ["tomato", "pasta", "olive oil"]
    },
    {
        "name": "Vegan with dairy",
        "dietary": "vegan",
        "forbidden": ["milk", "cheese", "eggs"],
        "allowed": ["tofu", "vegetables"]
    },
    {
        "name": "Pescatarian with meat",
        "dietary": "pescatarian",
        "forbidden": ["chicken", "beef", "pork"],
        "allowed": ["salmon", "shrimp"]
    }
]

# Run tests
for test in test_cases:
    output = test_model(test)
    assert not any(item in output for item in test["forbidden"])
    print(f"✅ {test['name']}: PASSED")
```

---

## Hyperparameter Tuning

### If Loss Not Decreasing

**Symptom**: Loss stays high (> 0.8) after 1000+ steps

**Solutions**:
1. Increase learning rate: `5e-5` → `8e-5`
2. Increase LoRA alpha: `16` → `20`
3. Check data quality

### If Overfitting

**Symptom**: Train loss << Val loss (e.g., 0.3 vs 0.8)

**Solutions**:
1. Decrease learning rate: `5e-5` → `3e-5`
2. Decrease LoRA alpha: `16` → `12`
3. Reduce epochs: `2` → `1`
4. Increase dropout: `0.05` → `0.1`

### If OOM (Out of Memory)

**Symptom**: Process killed with memory error

**Solutions**:
1. ✅ Already using batch_size=1 (minimum)
2. Reduce max_seq_length: `2048` → `1536`
3. Close other applications
4. Use gradient checkpointing: `grad_checkpoint: true` (slower but saves memory)

---

## Troubleshooting

### Common Issues

#### 1. MLX Not Found
```bash
# Error: ModuleNotFoundError: No module named 'mlx'

# Solution:
pip install mlx mlx-lm

# Verify:
python -c "import mlx; print(mlx.__version__)"
```

#### 2. Model Download Failure
```bash
# Error: Failed to download model

# Solution: Manual download
huggingface-cli download mlx-community/Phi-3-mini-4k-instruct-4bit
```

#### 3. Data Format Error
```bash
# Error: KeyError: 'text'

# Solution: Verify data format
python -c "
import json
with open('data/finetune/train.jsonl') as f:
    sample = json.loads(f.readline())
    assert 'text' in sample
    print('✅ Format correct')
"
```

#### 4. Slow Training (< 0.2 it/sec)
```bash
# Check CPU/GPU usage
top -pid $(pgrep -f mlx_lm)

# Solution:
# 1. Close other applications
# 2. Verify not using swap memory
# 3. Reduce max_seq_length if many long sequences
```

#### 5. Training Stops Without Error
```bash
# Check system logs
log show --predicate 'process == "mlx_lm"' --last 1h

# Common cause: macOS put process to sleep
# Solution: Disable App Nap for Terminal
# System Preferences → Battery → Prevent automatic sleeping
```

---

## Best Practices

### During Training

1. **Don't run other heavy programs**
   - Keep memory usage < 20 GB total
   - Training uses ~15 GB at peak

2. **Monitor first 500 steps**
   - Loss should start decreasing
   - If not, stop and adjust hyperparameters

3. **Save checkpoints**
   - Default: every 500 steps
   - Keep at least last 3 checkpoints

4. **Let Mac cool down**
   - Training generates heat
   - Ensure good ventilation

### After Training

1. **Test immediately**
   - Run dietary constraint tests
   - Compare to V2 performance

2. **Backup adapter**
   - Copy to safe location
   - Upload to DVC/GCS

3. **Document results**
   - Final train/val loss
   - Test case pass rate
   - Any issues encountered

---

## Performance Expectations

### Training Time

| Phase | Duration | Progress |
|-------|----------|----------|
| Model loading | 1-2 min | 0% |
| Initial validation | 30 sec | 0.01% |
| Epoch 1 (4500 steps) | 2.5 hours | 50% |
| Epoch 2 (4500 steps) | 2.5 hours | 100% |
| **Total** | **~5-6 hours** | **100%** |

### Resource Usage

| Resource | Usage | Notes |
|----------|-------|-------|
| Memory | 10-15 GB | Peak during validation |
| CPU | 60-80% | Metal acceleration |
| Disk I/O | Minimal | Only on checkpoint saves |
| Power | ~30-40W | M4 Pro efficient |

---

## Next Steps

After successful training:

1. **Validate**: Run full test suite
2. **Compare**: V2 vs V3 performance
3. **Deploy**: Update backend with new adapter
4. **Monitor**: Production dietary constraint success rate

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review MLX documentation: https://ml-explore.github.io/mlx/
- Check Phi-3 model card: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct

---

**Training Status**: Ready ✅
**Estimated Completion**: ~5-6 hours from start ✅
**Success Rate**: High (conservative hyperparameters) ✅

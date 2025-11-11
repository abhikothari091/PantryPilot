# Phi-3 Mini Fine-tuning V3: Dietary Constraint Fix

## Overview

This project addresses a critical production failure in our recipe generation model: despite achieving 97.8% validation accuracy, the fine-tuned Phi-3 Mini model incorrectly selected meat ingredients for vegetarian recipes in production.

## Problem Statement

**Symptom**: Fine-tuned model fails dietary constraint validation in production
- Validation accuracy: 97.8%
- Production failure: Selects chicken breast for vegetarian recipes
- Root cause: Distribution shift + overfitting

## Root Cause Analysis

### 1. Distribution Shift
- **Training data**: Chicken stock (11.5% presence)
- **Production data**: Chicken breast (17% presence)
- Model never learned to avoid chicken breast in vegetarian context

### 2. Over-aggressive Fine-tuning
- Learning rate too high (1e-4)
- Too many epochs (3)
- LoRA alpha too high (20)
- Led to overfitting on training distribution

### 3. Training Data Bias
- 849 vegetarian samples had "chicken stock" in inventory
- These samples correctly avoided chicken stock
- But lack of diversity in meat/fish types

## Solution: V3 Approach

### Data Strategy
1. **Balanced Dataset**: 5,000 samples across 10 cuisines
2. **Diverse Augmentation**: 40% of vegetarian samples include diverse meat/fish in inventory
   - Poultry, beef, pork, fish, seafood (2-3 items per sample)
   - All marked as `forbidden: true`
3. **Zero Violations**: 100% clean training data (verified)

### Training Strategy
1. **Conservative Hyperparameters**:
   - Learning rate: 5e-5 (down from 1e-4)
   - Epochs: 2 (down from 3)
   - LoRA alpha: 16 (down from 20)
   - Batch size: 1 (memory safe)

2. **Platform**: MLX on Apple Silicon (M4 Pro)
   - Stable, tested environment
   - ~5-6 hours training time

## Project Structure

```
phi3_finetuning_v3/
├── README.md                          # This file
├── data_preparation/
│   ├── scripts/                       # 6-step data pipeline
│   │   ├── 1_analyze_recipe_distribution.py
│   │   ├── 2_generate_synthetic_cuisine.py
│   │   ├── 3_sample_balanced_recipes.py
│   │   ├── 4_merge_and_augment.py
│   │   ├── 5_generate_enriched_training_data.py
│   │   └── 6_split_and_clean_training_data.py
│   └── README.md
├── data/
│   ├── intermediate/                  # DVC tracked
│   │   ├── balanced_samples_4334.json
│   │   ├── synthetic_korean_286.json
│   │   └── synthetic_vietnamese_273.json
│   └── final/                         # Git + DVC
│       ├── train.jsonl               # 4,500 samples
│       ├── valid.jsonl               # 500 samples
│       └── enriched_training_data_5000.json
├── training/
│   ├── finetune_mlx_v3.py
│   ├── lora_config_v3.yaml
│   ├── colab_finetune_phi3_v3_fixed.ipynb
│   └── README.md
├── analysis/
│   ├── analyze_violation_pattern.py
│   └── reports/
│       └── validation_summary.csv
└── docs/
    ├── PROBLEM_ANALYSIS.md           # Detailed problem analysis
    ├── DATA_PIPELINE.md              # Data generation process
    └── TRAINING_GUIDE.md             # Training instructions
```

## Quick Start

### 1. Data Preparation (if regenerating)

```bash
cd data_preparation/scripts

# Step 1: Analyze Recipe1M distribution
python 1_analyze_recipe_distribution.py

# Step 2: Generate synthetic recipes for underrepresented cuisines
python 2_generate_synthetic_cuisine.py

# Step 3: Sample balanced recipes from Recipe1M
python 3_sample_balanced_recipes.py

# Step 4: Merge and augment with diverse meat/fish
python 4_merge_and_augment.py

# Step 5: Generate enriched training data
python 5_generate_enriched_training_data.py

# Step 6: Split and clean
python 6_split_and_clean_training_data.py
```

### 2. Fine-tuning

**Using MLX (Mac M4 Pro - Recommended)**:
```bash
cd training
python finetune_mlx_v3.py  # Shows configuration
mlx_lm.lora --config lora_config_v3.yaml
```

**Using Google Colab (T4 GPU)**:
- Upload `colab_finetune_phi3_v3_fixed.ipynb` to Colab
- Select T4 GPU runtime
- Upload `train.jsonl` and `valid.jsonl`
- Run cells sequentially

## Key Metrics

### Dataset Statistics
- **Total samples**: 5,000 (4,500 train / 500 valid)
- **Cuisines**: 10 (balanced distribution)
- **Dietary diversity**: 30% vegetarian, 70% omnivore/pescatarian
- **Augmented samples**: 600 (40% of vegetarian)
- **Dietary violations**: 0 (100% clean)

### Training Configuration
| Parameter | V2 (Failed) | V3 (Current) | Rationale |
|-----------|-------------|--------------|-----------|
| Learning Rate | 1e-4 | 5e-5 | More conservative |
| Epochs | 3 | 2 | Prevent overfitting |
| LoRA Alpha | 20 | 16 | Reduce learning magnitude |
| Batch Size | 2-4 | 1 | Memory safe |
| Data Size | 4,059 | 5,000 | More diverse |

### Expected Results
- Training time: ~5-6 hours (MLX, batch 1)
- Peak memory: ~15 GB
- Validation loss target: < 0.6
- Production accuracy target: > 95%

## Data Versioning

### DVC Configuration
- **Remote**: Google Cloud Storage (`gs://pantrypilot-mlops/dvc-storage`)
- **Git + DVC**: `train.jsonl`, `valid.jsonl` (immediate access + versioning)
- **DVC only**: Intermediate files, models (save Git space)

### Pulling Data
```bash
# Pull all DVC-tracked data
dvc pull

# Pull specific files
dvc pull data/final/train.jsonl.dvc
```

## Model Deployment

After training completes:

1. **Test the adapter**:
```python
from mlx_lm import load, generate

model, tokenizer = load(
    "mlx-community/Phi-3-mini-4k-instruct-4bit",
    adapter_path="models/phi3-recipe-lora-v3"
)
```

2. **Update backend**:
```python
# recipe-app/backend/model_service.py
ADAPTER_PATH = "models/phi3-recipe-lora-v3"
```

3. **Validate with test cases**:
- Vegetarian with chicken breast in inventory
- Vegan with dairy/eggs in inventory
- Pescatarian with meat in inventory

## Documentation

- [PROBLEM_ANALYSIS.md](docs/PROBLEM_ANALYSIS.md): Detailed analysis of the production failure
- [DATA_PIPELINE.md](docs/DATA_PIPELINE.md): Step-by-step data generation process
- [TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md): Comprehensive training instructions

## Key Improvements from V2

1. ✅ **Diverse meat/fish augmentation**: Not just chicken, but 5 categories
2. ✅ **Balanced cuisine distribution**: 10 cuisines, ~500 samples each
3. ✅ **Conservative training**: Lower LR, fewer epochs, smaller alpha
4. ✅ **Zero violations**: All augmented samples verified clean
5. ✅ **Comprehensive metadata**: Full traceability of data sources

## Timeline

- **Data Generation**: 2 days (analysis + generation + validation)
- **Training**: 5-6 hours (MLX on M4 Pro)
- **Validation**: 1 day (testing + comparison)
- **Total**: ~4 days

## Contributors

- Data Pipeline: Recipe1M analysis + synthetic generation
- Fine-tuning: MLX optimization for Apple Silicon
- Validation: Dietary constraint testing

## License

Internal project for PantryPilot MLOps

---

**Status**: Training in progress (Iter 900/9000, ~10% complete)
**Expected Completion**: Morning of Nov 12, 2025

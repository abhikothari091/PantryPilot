# Data Preparation Scripts

## Overview

This directory contains 6 scripts that form the complete data generation pipeline for Phi-3 Mini V3 fine-tuning.

## Pipeline Flow

```
1_analyze_recipe_distribution.py
         ↓
2_generate_synthetic_cuisine.py
         ↓
3_sample_balanced_recipes.py
         ↓
4_merge_and_augment.py
         ↓
5_generate_enriched_training_data.py
         ↓
6_split_and_clean_training_data.py
```

## Scripts

### 1. analyze_recipe_distribution.py
**Purpose**: Analyze Recipe1M dataset distribution
**Output**: Console statistics
**Time**: ~5-10 minutes

### 2. generate_synthetic_cuisine.py
**Purpose**: Generate Korean/Vietnamese recipes using LLM
**Output**: synthetic_korean_286.json, synthetic_vietnamese_273.json
**Time**: ~2.5 hours
**Requires**: Ollama + Llama 3.1 8B

### 3. sample_balanced_recipes.py
**Purpose**: Sample balanced recipes from Recipe1M
**Output**: balanced_samples_4334.json
**Time**: ~2-3 minutes

### 4. merge_and_augment.py
**Purpose**: Merge datasets + augment with diverse meat/fish
**Output**: merged_augmented_4893.json
**Time**: ~1-2 minutes

### 5. generate_enriched_training_data.py
**Purpose**: Generate complete Phi-3 training samples with LLM
**Output**: enriched_training_data_5000.json
**Time**: ~4.5 hours
**Requires**: Ollama + Llama 3.1 8B

### 6. split_and_clean_training_data.py
**Purpose**: Split train/valid + verify zero violations
**Output**: train.jsonl (4500), valid.jsonl (500)
**Time**: ~30 seconds

## Quick Start

```bash
cd scripts

# Run all steps in order
python 1_analyze_recipe_distribution.py
python 2_generate_synthetic_cuisine.py
python 3_sample_balanced_recipes.py
python 4_merge_and_augment.py
python 5_generate_enriched_training_data.py
python 6_split_and_clean_training_data.py
```

## Total Time
~7 hours (mostly LLM generation)

## Documentation
See [../docs/DATA_PIPELINE.md](../docs/DATA_PIPELINE.md) for detailed explanation.

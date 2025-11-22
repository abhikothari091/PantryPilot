# DPO Training Pipeline - Personalized Recipe Generation

## Overview

This pipeline implements **Direct Preference Optimization (DPO)** to create personalized recipe generation models for different user personas. DPO fine-tunes the base SFT model using preference pairs (chosen/rejected recipes) to align model outputs with specific user preferences.

### Key Concepts

- **Personas**: 6 user archetypes with distinct dietary preferences and restrictions
- **Preference Pairs**: Chosen (good) vs Rejected (bad) recipe pairs labeled by Llama 70B
- **DPO Training**: Aligns model outputs with persona preferences using preference optimization
- **Evaluation**: Gemini 2.0 Flash evaluates DPO models against SFT baseline

### Pipeline Stages

```
1. Variant Generation → 2. Preference Labeling → 3. DPO Training → 4. Evaluation
   (SFT Model)            (Llama 70B via Groq)    (Lambda Labs)     (Vertex AI Gemini)
```

---

## 1. Prerequisites

### 1.1 Environment Setup

```bash
cd model_development/training_pipeline/05_dpo_training

# Install dependencies
pip install -r requirements.txt

# For evaluation
pip install -r evaluation/requirements.txt
```

### 1.2 Required Models & Data

**SFT Model**: The pipeline requires the SFT (Supervised Fine-Tuned) model from stage `04_training/`.

```bash
# Download SFT model if not available
cd ../04_training
# Follow instructions in 04_training/README.md to get the SFT model
```

**Base Model**: Llama 3.2 3B Instruct (downloaded automatically by Hugging Face)

### 1.3 API Keys

Create a `.env` file in the `05_dpo_training/` directory:

```bash
# Groq API (for preference labeling) - FREE
GROQ_API_KEY=your_groq_api_key

# Google Cloud (for training & evaluation)
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

**Get Groq API Key**: https://console.groq.com/keys (FREE, no credit card)

---

## 2. Personas

Six user personas with distinct preferences:

| Persona ID | Name | Cuisine | Dietary Restrictions | Forbidden Ingredients |
|-----------|------|---------|---------------------|---------------------|
| `persona_a_korean_spicy` | Korean Food Lover | Korean, Asian | None | - |
| `persona_b_indian_veg` | Indian Vegetarian | Indian | Vegetarian | Meat, chicken, beef, pork, seafood |
| `persona_c_italian_gf` | Italian Gluten-Free | Italian, Mediterranean | Gluten-free | Wheat, pasta, bread, flour |
| `persona_d_japanese_lowsodium` | Japanese Low-Sodium | Japanese | Low-sodium | Soy sauce, miso, salt |
| `persona_e_mexican_vegan` | Mexican Vegan | Mexican, Latin | Vegan | Meat, dairy, eggs, cheese |
| `persona_f_chinese_keto` | Chinese Keto | Chinese | Keto | Rice, noodles, sugar, carbs |

See [personas.yaml](personas.yaml) for complete definitions.

---

## 3. Pipeline Execution

### 3.1 Stage 1: Generate Variants

Generate 2 recipe variants per prompt (500 prompts per persona):

- **Variant A**: Strong persona constraints (temperature=0.7)
- **Variant B**: Weak/no constraints (temperature=0.9)

```bash
cd scripts/

# Generate for all personas (3,000 total variants)
python generate_variants.py \
  --base_model meta-llama/Llama-3.2-3B-Instruct \
  --adapter ../../04_training/llama3b_lambda_lora \
  --personas_config ../personas.yaml \
  --output_dir ../data/variants \
  --count 500

# Or generate for single persona
python generate_variants.py --persona persona_a_korean_spicy --count 100
```

**Output**: `data/variants/{persona}_variants.jsonl`

**Time**: ~2-3 hours (local GPU or M1/M2 Mac with MPS)

### 3.2 Stage 2: Label Preferences

Use Llama 70B (via Groq API) to label chosen/rejected pairs:

```bash
python groq_choose_preference.py \
  --variants_dir ../data/variants \
  --output_dir ../data/preference_pairs \
  --personas_config ../personas.yaml

# Or for single persona
python groq_choose_preference.py --persona persona_a_korean_spicy
```

**Labeling Criteria**:
1. Dietary restrictions compliance
2. Forbidden ingredients avoided
3. Cuisine/flavor alignment
4. Overall persona match

**Output**: `data/preference_pairs/{persona}_dpo_pairs.jsonl`

**Cost**: FREE (Groq beta)
**Time**: ~30-45 minutes for 3,000 evaluations
**Pass Rate**: ~80-90% (400-450 pairs per persona)

### 3.3 Stage 3: Format for DPO

Convert to standard DPO training format (ChatML):

```bash
python format_for_dpo_chatml.py \
  --input_dir ../data/preference_pairs \
  --output_dir ../data/dpo_formatted
```

**Output Format**:
```json
{
  "prompt": "<|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n",
  "chosen": "{better recipe JSON}",
  "rejected": "{worse recipe JSON}"
}
```

**Output**: `data/dpo_formatted/{persona}_dpo_train.jsonl`

### 3.4 Stage 4: DPO Training

Train personalized models using DPO on Lambda Labs A100:

**Single Persona**:
```bash
python train_dpo_persona.py \
  --persona persona_a_korean_spicy \
  --base_model meta-llama/Llama-3.2-3B-Instruct \
  --sft_adapter ../../04_training/llama3b_lambda_lora \
  --train_data ../data/dpo_formatted/persona_a_korean_spicy_dpo_train.jsonl \
  --output_dir ../trained_models/persona_a_korean_spicy_v1.0
```

**All Personas** (batch):
```bash
./train_all_personas.sh
```

**Training Configuration**:
```python
learning_rate: 5e-5
beta: 0.1  # KL divergence penalty
epochs: 3
batch_size: 4
gradient_accumulation: 4  # Effective batch = 16
optimizer: paged_adamw_8bit
bf16: True  # BF16 for A100
```

**LoRA Configuration**:
```python
rank: 16
alpha: 16
target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
dropout: 0.05
```

**Hardware**: Lambda Labs A100 40GB
**Cost**: ~$3-5 total (6 personas × ~$0.50-0.80 each)
**Time**: 30-45 min per persona

**Output**: `trained_models/{persona}_v1.0/` (~173MB each)

---

## 4. Model Management

### 4.1 Download Pre-trained Models

```bash
# Download all DPO models from GCS
./download_dpo_models.sh

# Download specific persona
./download_dpo_models.sh persona_a_korean_spicy
```

**GCS Location**: `gs://pantrypilot-dpo-models/v1.0/`

### 4.2 Upload Trained Models

```bash
# Upload to GCS
gcloud storage cp -r trained_models/persona_a_korean_spicy_v1.0 \
  gs://pantrypilot-dpo-models/v1.0/
```

### 4.3 Data Versioning with DVC

```bash
# Track data with DVC
dvc add data/

# Push to remote (GCS)
dvc push

# Pull data on another machine
dvc pull
```

**DVC Remote**: Configured in `.dvc/config` (GCS)

---

## 5. Evaluation

Evaluate DPO models against SFT baseline using Vertex AI (Gemini 2.0 Flash):

### 5.1 Run Evaluation

```bash
cd evaluation/

# Evaluate all personas (120 test cases)
python evaluate_dpo_personas.py \
  --project_id YOUR_GCP_PROJECT_ID \
  --personas all \
  --count 20 \
  --evaluators gemini-flash \
  --output_dir reports

# Evaluate single persona
python evaluate_dpo_personas.py \
  --project_id YOUR_GCP_PROJECT_ID \
  --personas persona_a_korean_spicy \
  --count 20
```

### 5.2 Test Cases

120 test cases (20 per persona) covering:
- **Basic Alignment** (8 tests): Perfect ingredient matches
- **Constraint Stress** (6 tests): Banned ingredients present
- **Edge Cases** (4 tests): Minimal ingredients, ambiguous requests
- **Cross-Persona** (2 tests): Different cuisine styles

See [evaluation/test_cases.yaml](evaluation/test_cases.yaml)

### 5.3 Evaluation Metrics

**Per-Test Scores** (0-10):
1. Persona alignment (cuisine style)
2. Constraint compliance (dietary restrictions)
3. Preferred ingredient usage
4. Recipe quality/structure
5. Overall suitability

**Aggregate Metrics**:
- **Win Rate**: DPO wins / total tests
- **Confidence**: high/medium/low distribution
- **Category Performance**: Breakdown by test type

### 5.4 Evaluation Results

**Cost**: ~$0.06 total (120 tests × $0.0005 each)
**Time**: 1-2 hours

**Reports**:
- `reports/evaluation_report.html` - Interactive visualization
- `reports/detailed_results.json` - Full evaluation data
- `reports/summary_stats.json` - Statistics

### 5.5 Expected Performance

Based on RecipeGen-LLM results:

- **Overall Win Rate**: 75.8% (91/120)
- **High Confidence Wins**: 68.3%
- **Best Performers**: persona_b (95%), persona_e (95%)
- **Weakest**: persona_f (50%)

---

## 6. Directory Structure

```
05_dpo_training/
├── README.md                      # This file
├── personas.yaml                  # Persona definitions
├── requirements.txt               # Python dependencies
├── download_dpo_models.sh         # GCS download script
├── data/                          # DVC-tracked data
│   ├── variants/                  # Generated variants
│   ├── preference_pairs/          # Labeled pairs
│   └── dpo_formatted/            # Training format
├── scripts/
│   ├── config.py                 # Configuration
│   ├── generate_variants.py      # Stage 1
│   ├── groq_choose_preference.py # Stage 2
│   ├── format_for_dpo_chatml.py  # Stage 3
│   ├── train_dpo_persona.py      # Stage 4
│   └── train_all_personas.sh     # Batch training
├── evaluation/
│   ├── evaluate_dpo_personas.py  # Main evaluator
│   ├── vertexai_evaluator.py    # Gemini interface
│   ├── model_loader.py           # Model utilities
│   ├── report_generator.py       # Report generation
│   ├── test_cases.yaml           # Test scenarios
│   ├── requirements.txt
│   └── reports/                  # Evaluation outputs
└── trained_models/                # DPO models (gitignored)
    ├── persona_a_korean_spicy_v1.0/
    ├── persona_b_indian_veg_v1.0/
    └── ...
```

---

## 7. Cost Breakdown

| Stage | Service | Cost |
|-------|---------|------|
| Variant Generation | Local GPU / M1 Mac | FREE |
| Preference Labeling | Groq (Llama 70B) | FREE |
| DPO Training | Lambda Labs A100 | ~$3-5 |
| Evaluation | Vertex AI (Gemini) | ~$0.06 |
| **Total** | | **~$3-6** |

---

## 8. Troubleshooting

### 8.1 CUDA Out of Memory

**DPO Training**:
```python
# Reduce batch size in train_dpo_persona.py
per_device_train_batch_size=2
gradient_accumulation_steps=8
```

### 8.2 MPS (Mac M1/M2) Issues

**Variant Generation**:
```bash
# If MPS fails, fallback to CPU
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

### 8.3 Groq API Rate Limits

**Preference Labeling**:
```python
# Reduce concurrent requests in groq_choose_preference.py
rate_limit = 30  # requests per minute
```

### 8.4 DVC Remote Not Configured

```bash
# Configure GCS remote
dvc remote add -d gcs gs://pantrypilot-dvc-storage
dvc remote modify gcs credentialpath /path/to/service-account-key.json
```

---

## 9. Future Enhancements

### 9.1 Automatic Retraining Pipeline

**Planned Features**:
- User feedback collection API
- Threshold monitoring (good/total ratio)
- Automatic DPO retraining trigger
- Train/test split validation
- A/B testing deployment

**Architecture**:
```
User Feedback → Threshold Check → DPO Retrain → Validation → Deploy
     ↓               ↓                ↓             ↓           ↓
  Neon DB      Airflow DAG       Lambda Labs    Test Set    GCS/K8s
```

### 9.2 MLflow Integration

**Experiment Tracking**:
```python
import mlflow

mlflow.log_params({"learning_rate": 5e-5, "beta": 0.1})
mlflow.log_metrics({"train_loss": loss})
mlflow.log_artifact("adapter_model.safetensors")
```

### 9.3 Model Registry

- Centralized model versioning
- Deployment approval workflow
- Performance benchmarking
- Rollback capabilities

---

## 10. References

- **DPO Paper**: [Direct Preference Optimization](https://arxiv.org/abs/2305.18290)
- **TRL Library**: [Hugging Face TRL](https://github.com/huggingface/trl)
- **Groq API**: [Groq Console](https://console.groq.com/)
- **Vertex AI**: [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)

---

## Questions or Issues?

For questions about this pipeline, please check:
1. RecipeGen-LLM documentation in `RecipeGen-LLM/` folder
2. Main PantryPilot README for general setup
3. Create an issue on GitHub

**Happy Training! 🚀**

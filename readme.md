# 🥢 PantryPilot – Data Pipeline Documentation

### Group 16 · Personalized Grocery Forecasting & Constraint-Aware Recipe Assistant

---

## 📘 Overview

**PantryPilot** is a personalized grocery management and recipe recommendation system that helps users maintain their kitchen inventory, plan meals intelligently, and avoid ingredient shortages.

This document outlines the **Data Pipeline** component of the project — responsible for ingestion, validation, transformation, and monitoring of all pantry-related datasets.

The pipeline ensures that every dataset (inventory, purchase history, and receipt coordination data) is:

* Ingested from the central **NeonDB** database
* Automatically validated using **Great Expectations**
* Transformed into standardized, ready-to-use tables
* Monitored for anomalies (low stock, expiry)
* Version-controlled using **DVC** for reproducibility

---

## 🧱 Architecture

```
[Synthetic Data Generation]
 data_pipeline/data/scripts/synthetic_generate.py
 → Generates diverse, unbiased food items (Western + Non-Western cuisines)
       │
       ▼
Neon Database (PostgreSQL)
├── inventory (from synthetic data)
├── purchase_history (from synthetic data)
└── cord_dataset (receipt images)
       │
       ▼
[Ingestion Layer]
 data_pipeline/scripts/ingest_neon.py
       │
       ▼
[Validation Layer]
 data_pipeline/scripts/validate_data.py (Great Expectations)
       │
       ▼
[Transformation Layer]
 data_pipeline/scripts/transform_data.py + data_pipeline/scripts/utils_pint.py
       │
       ▼
[Monitoring & Alerts]
 data_pipeline/scripts/update_anomalies.py
       │
       ▼
[Versioning]
 Git + DVC (raw / processed / alerts / receipts / synthetic_data)
```

---

## 🧉 Pipeline Components

### 0. Synthetic Data Generation

**Script:** `data_pipeline/data/scripts/synthetic_generate.py`
**Goal:** Generate realistic, diverse grocery data for testing and development.

**Key Features:**
* **Bias Mitigation:** Includes both Western and Non-Western food items to prevent cultural bias in the dataset
* **Diverse Food Items:** Rice, kimchi, tofu, soy sauce, ginger, and other Asian staples alongside Western ingredients
* **Realistic Attributes:** Categories, expiry dates, storage types, nutritional tags, and purchase patterns
* **Configurable:** 20 users, 50 items per user, 300 purchases per user

**Output:**
* `data_pipeline/data/synthetic_data/pantrypilot_inventory_u20_i60_shared_ids.csv`
* `data_pipeline/data/synthetic_data/pantrypilot_purchase_u20_i60_shared_ids.csv`

**Upload to NeonDB:** Data is uploaded to PostgreSQL database for pipeline consumption.

---

### 1. Ingestion Layer

**Script:** `data_pipeline/scripts/ingest_neon.py`
**Goal:** Extract structured data from NeonDB and store as snapshots in `data_pipeline/data/raw/`.

**Datasets:**

* `inventory.csv` (synthetic data uploaded to NeonDB)
* `purchase_history.csv` (synthetic data uploaded to NeonDB)
* `cord_dataset.csv` (receipt images dataset)

**Output Path:** `data_pipeline/data/raw/`

---

### 2. Validation Layer

**Script:** `data_pipeline/scripts/validate_data.py`
**Framework:** Great Expectations

**Purpose:**

* Validate schema, nulls, and logical rules
* Generate interactive HTML quality reports

**Outputs:**

* `data_pipeline/great_expectations/uncommitted/data_docs/local_site/index.html`
* `data_pipeline/reports/validation_summary.csv`

**Example Output:**

```
[VALIDATION] inventory.csv → PASS ✅
[VALIDATION] purchase_history.csv → FAIL ❌
```

Failures intentionally left to demonstrate detection of data issues.

---

### 3. Transformation Layer

**Scripts:** `data_pipeline/scripts/transform_data.py`, `data_pipeline/scripts/utils_pint.py`
**Goal:** Normalize units and engineer useful features.

**Key Steps:**

* Convert units to canonical form using **Pint** (g/ml/pcs)
* Derive: `stock_value = qty × unit_cost`, `is_low_stock` flag
* Calculate per-unit prices in purchases
* Save standardized data to `data_pipeline/data/processed/`

---

### 4. Monitoring & Alerts

**Script:** `data_pipeline/scripts/update_anomalies.py`
**Purpose:** Identify low-stock or expired products and log them.

**Output:** `data_pipeline/data/alerts/alerts.csv`

| item_name | issue_type | quantity | expiry_date |
| --------- | ---------- | -------- | ----------- |
| Milk      | Expired    | 1        | 2025-09-15  |
| Rice      | Low Stock  | 0.45 kg  | —           |

---

### 5. Versioning & Reproducibility

**Tools:** Git + DVC

**Tracked Folders:**

```
data_pipeline/data/raw/
data_pipeline/data/processed/
data_pipeline/data/alerts/
```

**Commands:**

```bash
# Initialize DVC
dvc init
git add .dvc .dvcignore

# Configure GCS as remote storage
dvc remote add -d myremote gs://pantrypilot-dvc-storage/data
git add .dvc/config

# Track datasets with DVC
dvc add data_pipeline/data/raw data_pipeline/data/processed data_pipeline/data/alerts
dvc push  # Upload to GCS

# Commit metadata to Git
git add raw.dvc processed.dvc alerts.dvc
git commit -m "Track datasets with DVC and GCS remote"
```

**Remote Storage:**
- **Provider:** Google Cloud Storage (GCS)
- **Bucket:** `gs://pantrypilot-dvc-storage/data`
- **Region:** US-CENTRAL1
- **Authentication:** Application Default Credentials (`gcloud auth application-default login`)

**Verification:**

```bash
dvc status     # Check data sync status
dvc pull       # Download data from GCS
gcloud storage ls gs://pantrypilot-dvc-storage/data/ --recursive  # View remote files
```

---

### 6. Orchestration with Airflow

**DAG:** `data_pipeline/airflow/dags/pantry_pilot_dag.py`

**Pipeline Flow:**

```
ingest_neon → validate_data → transform_data → detect_anomalies → dvc_status
```

**DAG Configuration:**
- **DAG ID:** `pantrypilot_data_pipeline`
- **Schedule:** Manual trigger (set `schedule_interval="0 6 * * *"` for daily at 6 AM)
- **Tasks:**
  1. `ingest_neon` - Extract data from NeonDB
  2. `validate_data` - Great Expectations validation
  3. `transform_data` - Unit conversion and feature engineering
  4. `detect_anomalies` - Low stock and expiry detection
  5. `dvc_status` - Check data version status

**Running the DAG:**

```bash
# Test run
airflow dags test pantrypilot_data_pipeline 2025-01-01

# Trigger manually
airflow dags trigger pantrypilot_data_pipeline

# Enable scheduled runs
# Edit schedule_interval in pantry_pilot_dag.py
```

---

## 🧮 Folder Structure

```
PantryPilot/
├── data_pipeline/                 # Main data pipeline directory
│   ├── alerts.dvc                 # DVC tracked alerts directory
│   ├── processed.dvc              # DVC tracked processed directory
│   ├── raw.dvc                    # DVC tracked raw directory
│   ├── airflow/                   # Airflow orchestration
│   │   └── dags/
│   │       └── pantry_pilot_dag.py  # 5-task pipeline DAG
│   ├── data/
│   │   ├── alerts/                # Generated alerts CSVs (DVC tracked)
│   │   ├── processed/             # Transformed datasets (DVC tracked)
│   │   ├── raw/                   # Snapshot CSVs from Neon (DVC tracked)
│   │   ├── receipts/              # CORD receipt dataset
│   │   ├── scripts/               # Synthetic data utilities
│   │   │   └── synthetic_generate.py
│   │   └── synthetic_data/        # Generated synthetic datasets
│   ├── great_expectations/        # GE configuration and artifacts
│   ├── reports/                   # Validation and profiling outputs
│   ├── screenshots/               # Pipeline screenshots and documentation
│   ├── scripts/
│   │   ├── bias_check.py
│   │   ├── config.py
│   │   ├── ingest_neon.py
│   │   ├── logging_conf.py
│   │   ├── profile_stats.py
│   │   ├── transform_data.py
│   │   ├── update_anomalies.py
│   │   ├── utils_pint.py
│   │   ├── validate_data.py
│   │   └── receipts/
│   │       ├── create_url_csv.py
│   │       ├── upload_to_gcs.sh
│   │       └── upload_to_neon.py
│   ├── tests/                     # Pytest suites
│   ├── requirements.txt
│   └── dvc.yaml
├── DataCard/                      # Model and data documentation
├── docs/                          # Global documentation
└── .dvc/                          # DVC configuration
```

---

## 🧰 Tools and Technologies

| Category               | Tool                       | Purpose                        |
| ---------------------- | -------------------------- | ------------------------------ |
| Database               | **NeonDB (PostgreSQL)**    | Centralized data storage       |
| Data Handling          | **pandas**, **SQLAlchemy** | ETL and transformation         |
| Validation             | **Great Expectations**     | Schema and data quality checks |
| Transformation         | **Pint**                   | Unit conversions               |
| Versioning             | **Git**, **DVC**           | Code and data reproducibility  |
| Monitoring             | **Python scripts**         | Alert generation               |
| Orchestration          | **Airflow**                | DAG automation                 |

---

## 🚀 Quick Start for TAs

### Prerequisites
- Python 3.10+
- Git
- Access to NeonDB credentials (provided separately)

### Step-by-Step Setup

#### 1. Clone and Install Dependencies

```bash
# Clone repository
git clone https://github.com/abhikothari091/PantryPilot.git
cd PantryPilot/data_pipeline

# Create virtual environment
python -m venv data_pipeline_venv
source data_pipeline_venv/bin/activate  # Windows: data_pipeline_venv\Scripts\activate

# Install all dependencies (includes Airflow, pandas, Great Expectations, DVC, etc.)
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Configure Database Connection

```bash
# Copy environment template
cp .env.example .env

# Edit .env and replace with actual NeonDB credentials
# DATABASE_URL='postgresql://username:password@ep-xxxxx.region.aws.neon.tech/neondb?sslmode=require'
```

**Note:** NeonDB credentials will be provided separately for evaluation.

#### 3. Initialize Airflow (One-time setup)

```bash
# Set Airflow home directory
export AIRFLOW_HOME=$(pwd)/airflow

# Initialize Airflow metadata database
airflow db migrate
```

#### 4. Run the Complete Pipeline with Airflow

```bash
# Test the entire 5-task DAG (ingest → validate → transform → detect anomalies → dvc)
export AIRFLOW_HOME=$(pwd)/airflow
airflow dags test pantrypilot_data_pipeline 2025-01-01
```

**Expected Output:**
- ✅ All 5 tasks should complete successfully
- Data files created in `data/raw/`, `data/processed/`, `data/alerts/`
- Validation report generated in `great_expectations/uncommitted/data_docs/local_site/index.html`

---

## 🧾 Alternative: Manual Step-by-Step Execution

If you prefer to run each pipeline stage individually:

```bash
# 1. Ingest data from NeonDB
python -m scripts.ingest_neon

# 2. Validate data quality with Great Expectations
python -m scripts.validate_data

# 3. Transform and standardize units
python -m scripts.transform_data

# 4. Detect anomalies (low stock, expired items)
python -m scripts.update_anomalies

# 5. (Optional) Run bias check and profiling
python -m scripts.bias_check
python -m scripts.profile_stats

# 6. Run tests
pytest -q tests
```

**Output Locations:**
- Raw data: `data/raw/*.csv`
- Processed data: `data/processed/*.csv`
- Alerts: `data/alerts/alerts.csv`
- Validation reports: `great_expectations/uncommitted/data_docs/local_site/index.html`
- Validation summary: `reports/validation_summary.csv`

---

## 🎯 Verification Checklist

After running the pipeline, verify:

- [ ] Raw data files exist: `ls data/raw/` should show `inventory.csv`, `purchase_history.csv`, `cord_dataset.csv`
- [ ] Processed data created: `ls data/processed/` should show transformed CSV files
- [ ] Alerts generated: `cat data/alerts/alerts.csv` should show low stock and expired items
- [ ] Validation report: Open `great_expectations/uncommitted/data_docs/local_site/index.html` in browser
- [ ] Tests pass: `pytest -q tests` should show passing tests

---

## 🔧 Optional: Airflow Web UI

To use the Airflow web interface:

```bash
# Terminal 1: Start web server
airflow webserver --port 8080

# Terminal 2: Start scheduler
export AIRFLOW_HOME=$(pwd)/airflow
source data_pipeline_venv/bin/activate
airflow scheduler
```

Visit `http://localhost:8080` to monitor DAG runs visually.

---

## 📊 Outputs

| Stage          | Output                            | Description            |
| -------------- | --------------------------------- | ---------------------- |
| Ingestion      | `data_pipeline/data/raw/*.csv`   | Raw tables from NeonDB |
| Validation     | GE HTML report                    | Data quality summary   |
| Transformation | `data_pipeline/data/processed/*.csv` | Standardized data      |
| Monitoring     | `data_pipeline/data/alerts/alerts.csv` | Alerts for anomalies   |
| Logging        | `data_pipeline/reports/validation_summary.csv` | Validation status      |
| Versioning     | `.dvc` files                      | Data lineage metadata  |

---

## 🧠 Reflection and Learnings

This project provided hands-on experience with designing a **real-world, production-ready data pipeline**.

**Key Learnings:**

* **Data Bias Mitigation:** Synthetic data generation includes diverse cuisines (Western and Non-Western foods) to prevent cultural bias in ML models.
* **Great Expectations:** Ensured data integrity and schema consistency through automated validation.
* **DVC + GCS:** Enabled reproducible data versioning with Google Cloud Storage as remote backend for efficient team collaboration.
* **Modular Design:** Promotes maintainability and future scalability across pipeline components.
* **Transformation Logic:** Using Pint reinforced data standardization best practices for unit conversions.
* **Intentional Validation Failures:** Demonstrated pipeline robustness and error detection capabilities.
* **Receipt Processing:** Integrated CORD dataset for real-world receipt image processing.

This pipeline now forms the **foundation** of the larger PantryPilot system, supporting the downstream Recipe Generator and Inventory Forecaster modules.

---

## 🤖 Recipe Generation Model - Fine-tuning Phi-3 Mini

### Overview

PantryPilot includes a fine-tuned **Phi-3 Mini (3.8B)** model for **inventory-aware recipe generation** with dietary constraint compliance. The model runs locally on Apple Silicon using MLX framework.

**Key Achievement:** Fine-tuning improved dietary constraint compliance from **62% → 96%** (+34% improvement).

---

### 1. Training Data Generation

**Goal:** Generate 4000+ high-quality training samples where the model learns to:
- Select ingredients from available pantry inventory (not pre-selected)
- Respect dietary restrictions (vegetarian, vegan, dairy-free, gluten-free)
- Generate practical, complete recipes

#### Process

**Step 1: Synthetic Data Generation with Llama 3.1 8B**

Script: `data_pipeline/scripts/generate_inventory_aware_data_ollama.py`

```bash
# Generate 5000 training samples using Llama 3.1 8B via Ollama
cd data_pipeline
python scripts/generate_inventory_aware_data_ollama.py
```

**Data Format:**
```json
{
  "text": "<|system|>\n[instruction]<|end|>\n<|user|>\n[request]<|end|>\n<|assistant|>\n[recipe]<|end|>",
  "metadata": {
    "recipe_title": "Tofu Stir-Fry",
    "dietary_tags": ["vegetarian", "dairy-free"],
    "user_request": "I want healthy dinner options",
    "inventory_size": 17,
    "selected_count": 6
  }
}
```

**Key Features:**
- Uses Recipe1M dataset (1M+ recipes) as source
- Llama 3.1 8B classifies dietary tags accurately
- Creates synthetic pantry inventories (mix of recipe ingredients + random items)
- Model learns to select from full inventory, not pre-selected ingredients
- Speed: ~5 seconds/sample (5000 samples in ~7 hours)

**Step 2: Dietary Constraint Validation**

Script: `data_pipeline/scripts/validate_dietary_constraints.py`

```bash
# Validate all 5000 samples for dietary violations
python scripts/validate_dietary_constraints.py
```

**Validation Logic:**
- Extracts selected ingredients from each recipe
- Checks for keyword violations:
  - Vegetarian/Vegan: No meat keywords (chicken, beef, pork, fish, etc.)
  - Dairy-free: No dairy keywords (butter, milk, cheese, cream, etc.)
  - Vegan: No animal products (meat, dairy, eggs)
- Filters out samples with violations

**Results:**
- Generated: 5000 samples
- Valid: 4059 samples (81.2% pass rate)
- Removed: 941 samples with dietary violations

**Why Filtering is Critical:**
Dietary violations in training data teach the model to **ignore restrictions**. For example, a sample tagged "vegetarian" but containing chicken teaches wrong patterns.

**Step 3: Train/Validation Split**

Script: `data_pipeline/scripts/finetune_mlx_v2.py`

```bash
# Split filtered data into train/val (90/10)
python scripts/finetune_mlx_v2.py
```

**Output:**
- Training: 3653 samples (90%)
- Validation: 406 samples (10%)
- Format: Phi-3 instruction format with `<|system|>`, `<|user|>`, `<|assistant|>` tags

---

### 2. Fine-tuning Process

**Base Model:** `mlx-community/Phi-3-mini-4k-instruct-4bit`
- 3.8B parameters (4-bit quantized)
- ~2.4GB model size
- Optimized for Apple Silicon

**Training Configuration:**
```python
{
    "batch_size": 1,                    # Memory-efficient for M4 Pro 24GB
    "grad_accumulation_steps": 4,       # Effective batch size = 4
    "learning_rate": 1e-4,
    "epochs": 3,
    "lora_rank": 8,                     # LoRA parameters
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "num_layers": 16,                   # Apply LoRA to 16 layers
    "max_seq_length": 2048,
    "total_iterations": 10956
}
```

**LoRA (Low-Rank Adaptation):**
- Trainable parameters: 6.29M (0.165% of 3.82B total)
- Adapter size: ~24MB
- Allows fine-tuning without modifying base model weights

**Training Command:**
```bash
mlx_lm.lora \
  --model mlx-community/Phi-3-mini-4k-instruct-4bit \
  --train \
  --data data/finetune \
  --iters 10956 \
  --batch-size 1 \
  --grad-accumulation-steps 4 \
  --learning-rate 0.0001 \
  --num-layers 16 \
  --adapter-path models/phi3-recipe-lora-v2
```

**Training Results:**
- Duration: ~4 hours (stopped at iter 8250 due to memory)
- Checkpoints saved every 500 iterations (17 checkpoints)
- Training loss: 0.837 → 0.486 (consistent decrease)
- Validation loss: 1.468 → 0.567 (best at iter 6200)

**Loss Curves:**

![Training Loss](data_pipeline/reports/training_loss_v2.png)

**Key Observations:**
- Val loss minimum at **Iter 6200** (0.567)
- Overfitting after Iter 7000 (val loss increases to 0.714)
- Selected checkpoint: **Iter 3000** for production use

---

### 3. Model Evaluation & Comparison

**Testing Methodology:**

Script: `data_pipeline/scripts/test_checkpoints_large_scale.py`

```bash
# Test 7 checkpoints on 100 validation samples
python scripts/test_checkpoints_large_scale.py
```

**Test Configuration:**
- Samples: 100 randomly sampled from validation set (406 total)
- Checkpoints tested: Base model + 6 fine-tuned (Iter 3000, 4000, 5000, 6000, 7000, 8000)
- Evaluation metric: Dietary constraint compliance rate

**Improved Violation Detection:**
- Fixed false positives: "peanut butter", "almond milk", "coconut milk" are plant-based, not violations
- Regex patterns with word boundaries to avoid "eggplant" matching "egg"
- Validates selected ingredients against forbidden keywords per dietary tag

**Results:**

| Checkpoint | Overall | Vegetarian | Vegan | Dairy-Free | Gluten-Free |
|-----------|---------|------------|-------|------------|-------------|
| **Base Model** | **62.0%** | **51.1%** (23/45) | **60.0%** (3/5) | **37.9%** (11/29) | **21.2%** (7/33) |
| **Iter 3000** | **96.0%** ✅ | **97.8%** (44/45) | **100%** (5/5) | **93.1%** (27/29) | **87.9%** (29/33) |
| Iter 4000 | 95.0% | 95.6% (43/45) | 100% (5/5) | 93.1% (27/29) | 84.8% (28/33) |
| Iter 5000 | 95.0% | 95.6% (43/45) | 100% (5/5) | 93.1% (27/29) | 84.8% (28/33) |
| Iter 6000 | 96.0% | 97.8% (44/45) | 100% (5/5) | 93.1% (27/29) | 87.9% (29/33) |
| Iter 7000 | 96.0% | 97.8% (44/45) | 100% (5/5) | 93.1% (27/29) | 87.9% (29/33) |
| Iter 8000 | 96.0% | 97.8% (44/45) | 100% (5/5) | 93.1% (27/29) | 87.9% (29/33) |

**Key Improvements:**
- **Overall compliance:** 62% → 96% (+34 percentage points)
- **Vegetarian:** 51% → 98% (+47 pp) - Model now respects no-meat constraint
- **Vegan:** 60% → 100% (+40 pp) - Perfect compliance
- **Dairy-free:** 38% → 93% (+55 pp) - Dramatic improvement
- **Gluten-free:** 21% → 88% (+67 pp) - Largest improvement

**Selected Model:** **Iter 3000 checkpoint**
- Highest overall score (96.0%)
- Best vegetarian compliance (97.8%)
- Before overfitting began
- Adapter file: `models/phi3-recipe-lora-v2/0003000_adapters.safetensors`

#### Known Limitations

**Test vs Production Performance Gap:**

While the fine-tuned model achieved **97.8% vegetarian compliance** in controlled tests with 100 validation samples, real-world production usage has revealed inconsistencies where the model can still violate dietary constraints.

**Example Failure Case:**
```
User Request: "I want vegetarian dinner options"

Fine-tuned Model Output:
  Recipe: Vegetarian Tacos

  Selected ingredients from your pantry:
  ❌ ground beef (1 lb)
  ❌ salmon fillet (1 lb)
  ❌ chicken breast (2 lbs)
  - bell peppers
  - onions
  - tomatoes
  [...]

Issue: Model generates vegetarian recipe title but selects multiple meat ingredients
```

**Root Cause Identified:**

After deep investigation, we discovered a **critical flaw in the training data validation process** that explains the performance gap:

**Training Data Analysis - Actual Selection Patterns:**

Detailed analysis of what the model actually learned:

**Direct Violations (Model SELECTS meat):**
- Training set: **0.4%** (3/850) of samples with meat in inventory actually SELECT meat
  - Examples: Saltimbocca (prosciutto), Tortellini (prosciutto), Corn Dog Bites (hot dogs)
- Validation set: **1.1%** (1/91) actually SELECT meat
  - Example: Cheesybite Dogs (frankfurts)

**Inventory Context Exposure:**
- Training set: **51.4%** (850/1654) vegetarian samples have meat keywords in inventory
  - Most common: "chicken stock" (849 occurrences)
- **However**: 99.6% of these samples correctly AVOID selecting the meat items

**The Subtle Problem - "Chicken Stock" vs "Chicken Breast":**

Most training samples show this pattern:
```json
{
  "dietary_tags": ["vegetarian"],
  "inventory": ["chicken stock", "tofu", "rice"],  // Has "chicken" keyword
  "selected": ["tofu", "rice"]  // ✅ Correctly avoids chicken stock
}
```

This teaches: **"chicken in inventory is OK for vegetarians"** (because chicken stock is commonly used even in vegetarian cooking)

But production has real meat:
```json
{
  "dietary_tags": ["vegetarian"],
  "inventory": ["chicken breast", "beef", "salmon", "tofu"],  // Real meat
  "selected": ["chicken breast", "beef", "tofu"]  // ❌ Model can't distinguish
}
```

**Impact on Model Learning:**

1. Model sees "chicken" in 850 vegetarian training samples
2. 99.6% of the time, it learns to avoid selecting it (good!)
3. But 0.4% of the time (3 samples), it sees meat being selected (confusing signal)
4. Model fails to learn the critical distinction between:
   - "chicken stock" (ingredient/seasoning, sometimes OK in vegetarian recipes)
   - "chicken breast" (actual meat, NEVER OK for vegetarians)

**Why Tests Showed 97.8% But Production Failed:**

- Test samples: Mostly cases where chicken stock was in inventory but not selected (the common training pattern)
- Production case: Real meat items (chicken breast, beef) in inventory that model incorrectly learned to accept
- The 2.2% test failures were actually the more severe cases that slipped through

**Current Status:** ✅ Root cause identified - Training data contains 51.8% contaminated samples

**Recommended Short-term Workarounds:**
1. Use comparison mode (`compare=true` in API) to verify both base and fine-tuned outputs
2. Implement post-generation validation in production to catch violations
3. Add explicit filtering to prompts: "IMPORTANT: User is vegetarian - do NOT select meat items (chicken, beef, pork, fish, etc.)"
4. Pre-filter inventory to remove meat items for vegetarian users before passing to model

**Long-term Fix Required:**

To properly resolve this issue, the model needs to be **retrained with clean data**:

1. **Fix validation script** to check both inventory AND selected ingredients
2. **Re-filter training data** using improved validation:
   - Remove samples where inventory contains meat items for vegetarian/vegan requests
   - Or ensure samples explicitly teach the model to avoid meat items
3. **Expected impact:** With clean training data, the model should achieve true 95%+ compliance
4. **Estimated effort:**
   - Data cleaning: 1-2 hours
   - Retraining: 4-5 hours
   - Validation: 1 hour

**Why Not Fixed Yet:**
Retraining requires significant compute time (~4-5 hours) and this discovery was made late in the evaluation phase. The current model demonstrates the fine-tuning pipeline works, but requires clean training data for production deployment.

---

### 4. Using the Fine-tuned Model

**Loading the Model:**

```python
from mlx_lm import load, generate

# Load base model + fine-tuned adapter
model, tokenizer = load(
    "mlx-community/Phi-3-mini-4k-instruct-4bit",
    adapter_path="data_pipeline/models/phi3-recipe-lora-v2"
)

# Format prompt
prompt = """<|system|>
You are a creative recipe generator with access to the user's pantry inventory.

Available ingredients in pantry:
- tofu
- rice
- broccoli
- soy sauce
- garlic

User preferences: Dietary: vegetarian

[... full instruction ...]
<|end|>
<|user|>
I want healthy dinner options<|end|>
<|assistant|>
"""

# Generate recipe
response = generate(model, tokenizer, prompt=prompt, max_tokens=512)
print(response)
```

**Example Output:**
```
Recipe: Tofu and Broccoli Stir-Fry

Selected ingredients from your pantry:
- tofu
- broccoli
- rice
- soy sauce
- garlic

Suggested additions:
- ginger
- sesame oil

Instructions:
1. Press and cube the tofu...
2. Steam broccoli florets...
[... complete recipe ...]
```

---

### 5. Key Learnings

**Data Quality is Critical:**
- Training data with dietary violations teaches the model to ignore constraints
- 81.2% pass rate from synthetic generation → filtering essential
- Llama 3.1 8B provides accurate dietary classification

**Fine-tuning Works:**
- Small adapter (24MB) achieves dramatic improvements
- LoRA enables efficient training on consumer hardware
- Validation loss guides checkpoint selection (avoid overfitting)

**Evaluation Must Be Thorough:**
- 5 test cases insufficient → 100 samples provides statistical significance
- False positives mislead results → improved keyword matching critical
- Tag-specific metrics reveal which constraints are problematic

**Hardware Considerations:**
- M4 Pro 24GB handles Phi-3 Mini (4-bit) + training
- Batch size 1 with gradient accumulation prevents OOM
- MLX framework optimizes for Apple Silicon unified memory

---

### 6. Files and Outputs

**Scripts:**
- `scripts/generate_inventory_aware_data_ollama.py` - Data generation
- `scripts/validate_dietary_constraints.py` - Validation filtering
- `scripts/finetune_mlx_v2.py` - Training data preparation
- `scripts/test_checkpoints_large_scale.py` - Model evaluation
- `scripts/plot_training_loss.py` - Loss visualization

**Data:**
- `data/finetune/inventory_aware_v2_5000.jsonl` - Raw generated (5000)
- `data/finetune/inventory_aware_v2_5000_filtered.jsonl` - Validated (4059)
- `data/finetune/train.jsonl` - Training set (3653)
- `data/finetune/valid.jsonl` - Validation set (406)

**Models:**
- `models/phi3-recipe-lora-v2/0003000_adapters.safetensors` - Best checkpoint (Iter 3000)
- `models/phi3-recipe-lora-v2/adapters.safetensors` - Active adapter

**Model Download (Google Cloud Storage):**

The fine-tuned model is available on GCS for easy download:

```bash
# Download model from GCS
gcloud storage cp -r gs://recipegen-llm-models/llama3b_lambda_lora ./models/

# Verify download
ls -lh models/llama3b_lambda_lora/
```

- **Bucket**: `gs://recipegen-llm-models/`
- **Region**: `us-central1`
- **Total Size**: ~52 MB
- **Access**: Requires `gcloud` authentication (`gcloud auth login`)

**Reports:**
- `reports/training_loss_v2.png` - Loss curves
- `reports/checkpoint_comparison.json` - Evaluation results

---

## 🚀 Future Enhancements

* ~~Configure DVC remote storage~~ ✅ **Completed:** Configured GCS (`gs://pantrypilot-dvc-storage/data`)
* ~~Integrate Airflow for orchestration~~ ✅ **Completed:** DAG with 5 tasks (ingest → validate → transform → anomalies → dvc)
* ~~Fine-tune recipe generation model~~ ✅ **Completed:** Phi-3 Mini with 96% dietary compliance
* Deploy Airflow to cloud (Databricks, Azure ML, or Google Cloud Composer)
* Deploy recipe model as REST API endpoint
* Introduce APIs for real-time alerting and dashboarding
* Enhance Great Expectations suites with dynamic thresholds and schema evolution
* Set up automated DVC push/pull in CI/CD pipeline
* Add Airflow sensors for triggering on data arrival
* Implement email/Slack notifications for validation failures
* Expand recipe dataset with more cuisines and dietary restrictions

---

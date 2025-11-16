🥢 PantryPilot – Data Pipeline & Model Development

Group 16 · Personalized Grocery Forecasting & Constraint-Aware Recipe Assistant

⸻

📘 High-Level Overview

PantryPilot is a personalized grocery management and recipe recommendation system that helps users:
	•	Maintain and monitor their kitchen inventory
	•	Plan meals based on available ingredients and preferences
	•	Avoid ingredient shortages through alerts and smart suggestions

The system is composed of two major technical pillars:
	1.	Data Pipeline (data_pipeline/)
	•	Ingestion from NeonDB (PostgreSQL)
	•	Validation with Great Expectations
	•	Transformation & feature engineering
	•	Monitoring & alerts for low-stock / expiry
	•	Data versioning with DVC + remote storage (GCS)
	•	Airflow DAG for orchestration
	2.	Model Development (model_development/)
	•	Synthetic recipe data generation & cleaning (teammate 2, separate training repo)
	•	LoRA fine-tuning of Llama 3.2 3B Instruct on ~11.8k curated recipes
	•	Local evaluation & benchmarking of base vs fine-tuned model
	•	Bias-focused slice evaluation across cuisines & dietary preferences
	•	Light CI checks that run smoke tests for both the data pipeline and LLM eval

This README describes both the data pipeline and the model development work, plus how they connect conceptually.

⸻

🧱 System Architecture

[Synthetic Data Generation for Inventory]
 data_pipeline/data/scripts/synthetic_generate.py
 → Generate diverse pantry items (Western + Non-Western cuisines)
       │
       ▼
Neon Database (PostgreSQL)
├── inventory (from synthetic_data)
├── purchase_history (from synthetic_data)
└── cord_dataset (receipt images metadata)
       │
       ▼
[Data Pipeline]
 data_pipeline/scripts/ingest_neon.py          # Ingestion from NeonDB
 data_pipeline/scripts/validate_data.py        # Great Expectations validation
 data_pipeline/scripts/transform_data.py       # Pint-based unit normalization
 data_pipeline/scripts/update_anomalies.py     # Low stock / expiry alerts
 DVC + Airflow orchestration
       │
       ▼
[Cleaned Inventory + History]
 data_pipeline/data/processed/*.csv
       │
       ▼
[Model Development]
 model_development/
  ├── (Teammate 2) Synthetic recipe generation + LoRA fine-tuning
  ├── (External) FastAPI + React app for recipe serving
  └── llm_eval/ (this project)
        ├── run_eval.py        # Base vs LoRA evaluation
        ├── metrics.py         # Parsing and metric computation
        ├── datasets.py        # Test data loader
        ├── bias_eval.py       # Bias slice evaluation
        └── reports/           # CSV/JSON outputs

In a fully integrated version of PantryPilot, the data pipeline outputs (clean inventory and history) would feed into the model inference layer to drive personalized recipe generation and inventory-aware suggestions.

⸻

🧉 Data Pipeline Components

0. Synthetic Inventory & Purchase Data
	•	Script: data_pipeline/data/scripts/synthetic_generate.py
	•	Goal: Generate realistic, diverse grocery data for development & testing.

Key Features:
	•	Bias mitigation: includes both Western and Non-Western food items
e.g. rice, kimchi, tofu, soy sauce, ginger, Indian spices, etc.
	•	Realistic attributes:
	•	Category (produce, dairy, pantry, etc.)
	•	Expiry dates
	•	Storage type (fridge, freezer, pantry)
	•	Nutritional tags
	•	Purchase patterns per user
	•	Configurable scale (current runs):
	•	~20 users
	•	~50–60 items per user
	•	~300 purchases per user

Outputs:
	•	data_pipeline/data/synthetic_data/pantrypilot_inventory_u20_i60_shared_ids.csv
	•	data_pipeline/data/synthetic_data/pantrypilot_purchase_u20_i60_shared_ids.csv

These synthetic CSVs are uploaded to NeonDB, where they appear as inventory and purchase_history tables used by the pipeline.

⸻

1. Ingestion Layer
	•	Script: data_pipeline/scripts/ingest_neon.py
	•	Goal: Extract structured data from NeonDB and store as CSV snapshots under data_pipeline/data/raw/.

Datasets:
	•	inventory.csv (synthetic inventory in NeonDB)
	•	purchase_history.csv (synthetic purchase history in NeonDB)
	•	cord_dataset.csv (receipt images metadata, for future OCR / VLM integration)

Output Path:
	•	data_pipeline/data/raw/

ingest_neon.py connects via SQLAlchemy using DB_URL from scripts/config.py, runs SELECT * on each table, and writes the results as CSV snapshots.

⸻

2. Validation Layer (Great Expectations)
	•	Script: data_pipeline/scripts/validate_data.py
	•	Framework: Great Expectations

Purpose:
	•	Validate schema and column types
	•	Check for nulls and invalid values
	•	Enforce logical rules (e.g., non-negative quantities)
	•	Generate interactive HTML quality reports

Outputs:
	•	HTML docs: data_pipeline/great_expectations/uncommitted/data_docs/local_site/index.html
	•	Summary CSV: data_pipeline/reports/validation_summary.csv

Example Outcome:

[VALIDATION] inventory.csv        → PASS ✅
[VALIDATION] purchase_history.csv → FAIL ❌ (intentional data issue for demo)

Intentional failures are left to demonstrate how the pipeline surfaces data quality problems.

⸻

3. Transformation Layer
	•	Scripts:
	•	data_pipeline/scripts/transform_data.py
	•	data_pipeline/scripts/utils_pint.py

Goal: Normalize all quantities and engineer useful features.

Key Steps (Inventory):
	•	Normalize units to canonical form (g, ml, pcs) using Pint via utils_pint.to_canonical.
	•	Compute stock_value = qty_canonical × unit_cost.
	•	Compute is_low_stock flag based on reorder_threshold.
	•	Write cleaned inventory to data_pipeline/data/processed/inventory_cleaned.csv.

Key Steps (Purchase History):
	•	Compute unit_price = price_total / quantity_purchased (safe division to avoid zero-division issues).
	•	Write cleaned purchase history to data_pipeline/data/processed/purchase_history_cleaned.csv.

⸻

4. Monitoring & Alerts
	•	Script: data_pipeline/scripts/update_anomalies.py
	•	Goal: Identify low-stock or expired items and log them as alerts.

Output: data_pipeline/data/alerts/alerts.csv

Example schema:

item_name	issue_type	quantity	expiry_date
Milk	Expired	1	2025-09-15
Rice	Low Stock	0.45 kg	—

These alerts can later be wired into a UI or notification system.

⸻

5. Versioning & Reproducibility (DVC + GCS)
	•	Tools: Git + DVC + Google Cloud Storage

Tracked folders:
	•	data_pipeline/data/raw/
	•	data_pipeline/data/processed/
	•	data_pipeline/data/alerts/

Example workflow:

cd data_pipeline

# Initialize DVC
dvc init

# Configure remote
dvc remote add -d myremote gs://pantrypilot-dvc-storage/data

# Track local data
dvc add data/raw data/processed data/alerts

# Push to remote
dvc push

# Commit metadata
git add data/*.dvc .dvc .dvcignore
git commit -m "Track datasets with DVC and GCS remote"

Verification commands:

dvc status   # Check if local and remote are in sync
dvc pull     # Download from GCS if needed

This ensures that every pipeline run is reproducible with a specific version of the raw/processed/alerts data.

⸻

6. Orchestration with Airflow
	•	DAG file: data_pipeline/airflow/dags/pantry_pilot_dag.py

Pipeline flow:

ingest_neon → validate_data → transform_data → detect_anomalies → dvc_status

DAG configuration:
	•	DAG ID: pantrypilot_data_pipeline
	•	Schedule: currently manual; can be set to "0 6 * * *" for daily 6 AM runs
	•	Tasks:
	1.	ingest_neon – Extract from NeonDB
	2.	validate_data – Run Great Expectations
	3.	transform_data – Perform unit conversions & feature engineering
	4.	detect_anomalies – Generate alerts
	5.	dvc_status – Check DVC sync state

Example test run:

export AIRFLOW_HOME=$(pwd)/airflow
airflow db migrate

# Dry-run the full DAG for a specific date
airflow dags test pantrypilot_data_pipeline 2025-01-01


⸻

🧮 Project Folder Structure (Updated)

PantryPilot/
├── data_pipeline/                      # Main data pipeline
│   ├── airflow/
│   │   └── dags/
│   │       └── pantry_pilot_dag.py
│   ├── data/
│   │   ├── alerts/
│   │   ├── processed/
│   │   ├── raw/
│   │   ├── receipts/
│   │   ├── scripts/
│   │   │   └── synthetic_generate.py
│   │   └── synthetic_data/
│   ├── great_expectations/
│   ├── reports/
│   ├── screenshots/
│   ├── scripts/
│   │   ├── bias_check.py
│   │   ├── config.py
│   │   ├── ingest_neon.py
│   │   ├── logging_conf.py
│   │   ├── profile_stats.py
│   │   ├── transform_data.py
│   │   ├── update_anomalies.py
│   │   ├── utils_pint.py
│   │   └── validate_data.py
│   ├── tests/
│   ├── requirements.txt
│   └── dvc.yaml
│
├── model_development/                  # Model dev & evaluation
│   ├── llm_eval/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── datasets.py
│   │   ├── metrics.py
│   │   ├── run_eval.py
│   │   ├── bias_eval.py
│   │   ├── analyze_results.py
│   │   ├── data/
│   │   │   ├── recipes_test.jsonl      # Synthetic eval set from teammate 2
│   │   │   └── val_bias.json           # Hand-crafted bias prompts
│   │   └── reports/
│   │       ├── eval_*.json
│   │       ├── eval_summary_*.csv
│   │       └── bias_report.csv
│   └── models/                         # NOT tracked by git (see .gitignore)
│       └── llama3b_lambda_lora/        # LoRA adapter (local, from GCS zip)
│
├── DataCard/                           # Data & model documentation
├── docs/                               # Global docs (slides, notes, etc.)
├── .github/
│   └── workflows/
│       └── pantrypilot_ci.yml          # CI pipeline (tests + smoke eval)
├── .dvc/                               # DVC configuration
└── .gitignore                          # Includes model_development/models/

Model artifacts under model_development/models/ are ignored by git to keep the repo lightweight. Instructions for fetching the LoRA adapter and base model are part of the model development section below.

⸻

🧰 Tools & Technologies

Area	Tools / Libraries
Database	NeonDB (PostgreSQL), SQLAlchemy
Data handling	pandas
Validation	Great Expectations
Units & transforms	Pint
Orchestration	Airflow
Versioning	Git + DVC + GCS remote
LLM base model	meta-llama/Llama-3.2-3B-Instruct
Fine-tuning	LoRA (PEFT), Lambda Labs GPU (teammate 2)
Inference & eval	Hugging Face Transformers, PEFT, PyTorch
Frontend / backend	React + FastAPI + MongoDB (external app repo)
CI	GitHub Actions (lint, tests, LLM eval smoke tests)


⸻

🚀 How to Run the Data Pipeline (Local)

1. Setup

# Clone repository
git clone https://github.com/abhikothari091/PantryPilot.git
cd PantryPilot/data_pipeline

# Virtual environment
python -m venv data_pipeline_venv
source data_pipeline_venv/bin/activate  # Windows: data_pipeline_venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

Configure database connection:

cp .env.example .env
# Edit .env and set DATABASE_URL for NeonDB

2. Manual step-by-step run

# 1. Ingest
python -m scripts.ingest_neon

# 2. Validate
python -m scripts.validate_data

# 3. Transform
python -m scripts.transform_data

# 4. Alerts
python -m scripts.update_anomalies

# 5. Optional profiling
python -m scripts.bias_check
python -m scripts.profile_stats

# 6. Tests
pytest -q tests

Outputs to verify:
	•	data/raw/*.csv → raw snapshots
	•	data/processed/*.csv → cleaned tables
	•	data/alerts/alerts.csv → anomalies
	•	great_expectations/uncommitted/data_docs/local_site/index.html → validation report
	•	reports/validation_summary.csv → validation summary

3. Airflow DAG run

export AIRFLOW_HOME=$(pwd)/airflow
airflow db migrate

# Test DAG
airflow dags test pantrypilot_data_pipeline 2025-01-01

Expected:
	•	All 5 tasks succeed
	•	Same artifacts as the manual run

⸻

🧠 Model Development: LLM Training & Evaluation

The model development work focuses on recipe generation conditioned on inventory and preferences, with a strong emphasis on:
	•	JSON schema adherence
	•	Dietary constraint adherence
	•	Cuisine matching
	•	Use of user inventory
	•	Behavior across dietary & cuisine slices (bias analysis)

A. Synthetic Recipe Data & LoRA Fine-Tuning (Teammate 2)

This section summarizes the external training workflow that produced the LoRA adapter used here.
	1.	Synthetic recipe generation (Groq + Llama 3.1 8B)
	•	Use Groq API with Llama 3.1 8B to generate ~12k synthetic recipes.
	•	Cover multiple realistic scenarios:
	•	Full inventory usage
	•	Pure dietary constraints (vegan, vegetarian, gluten-free, dairy-free)
	•	Cuisine-specific prompts (Italian, Chinese, Mexican, Indian, Japanese, Korean, etc.)
	•	Combined constraints (e.g., vegan Italian, gluten-free Mexican)
	•	User-requested ingredients (all present / partial match scenarios)
	•	Force JSON output with fields: recipe name, cuisine, culinary_preference, time, main_ingredients, steps, note, shopping_list.
	2.	ChatML conversion & cleaning
	•	Convert each example into a ChatML-style conversation:
	•	system: instructions for the recipe generator
	•	user: inventory + preference request
	•	assistant: JSON recipe
	•	Apply validation rules:
	•	Check vegan/vegetarian/gluten-free/dairy-free compliance
	•	Drop recipes that violate constraints (e.g., honey in vegan, soy sauce in gluten-free)
	•	Result: ~11,850 clean training examples.
	3.	LoRA fine-tuning on Lambda Labs
	•	Base model: meta-llama/Llama-3.2-3B-Instruct.
	•	Method: LoRA via PEFT.
	•	Typical config:
	•	Rank r = 16, alpha = 32
	•	Target modules: q_proj, k_proj, v_proj, o_proj
	•	~3 epochs, AdamW, cosine LR schedule
	•	Output: LoRA adapter folder (not tracked by git), distributed to teammates as a zip.

B. Model Artifacts & Storage
	•	Local location (ignored by git):
	•	model_development/models/llama3b_lambda_lora/
	•	Remote storage (GCS):
	•	Bucket: gs://pantrypilot-dvc-storage/data
	•	Model path (zip): gs://pantrypilot-dvc-storage/data/models/llama3b_lambda_lora.zip

Workflow (expected):
	1.	Download llama3b_lambda_lora.zip from the shared GCS bucket (or other internal sharing mechanism).
	2.	From repo root:

mkdir -p model_development/models
cd model_development/models
unzip /path/to/llama3b_lambda_lora.zip
# This should create model_development/models/llama3b_lambda_lora/

	3.	Ensure .gitignore excludes model_development/models/ so weights are never pushed.

The base model (meta-llama/Llama-3.2-3B-Instruct) is pulled from Hugging Face at runtime. If it is gated, users must configure HF_TOKEN or run huggingface-cli login.

⸻

C. LLM Evaluation: Base vs LoRA (llm_eval/)

All evaluation logic lives in model_development/llm_eval/.

1. Config & datasets
	•	config.py defines:
	•	PROJECT_ROOT: repo root as a Path
	•	BASE_MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
	•	LORA_ADAPTER_DIR: path to models/llama3b_lambda_lora/
	•	MAX_NEW_TOKENS: generation length cap (e.g., 256)
	•	TEMPERATURE_GRID: list of temperatures to evaluate (e.g., [0.7])
	•	datasets.py:
	•	Defines RecipeTestExample dataclass:

@dataclass
class RecipeTestExample:
    user_inventory: List[str]
    preference: Optional[str]
    cuisine: Optional[str]
    user_request: Optional[str]
    requested_ingredients: List[str]
    gold_output: Dict[str, Any]
    scenario: str
    generated_at: str


	•	Implements load_recipes_test() which reads recipes_test.jsonl from the shared recipes folder and constructs RecipeTestExample objects.

2. Prompting & generation
run_eval.py sets a strict SYSTEM_PROMPT for RecipeGen, which instructs the model to:
	•	Always return exactly one valid JSON object
	•	Never output markdown, backticks, or extra text
	•	Follow this schema:

{
  "status": "ok",
  "missing_ingredients": ["..."],
  "recipe": {
    "name": "...",
    "cuisine": "...",
    "culinary_preference": "...",
    "time": "...",
    "main_ingredients": ["..."],
    "steps": "Step 1. ...",
    "note": null
  },
  "shopping_list": ["..."]
}

…and follow strict rules like:
	•	Do not list more than 8 missing_ingredients
	•	Use inventory as the main source of main_ingredients
	•	Respect preference (vegan, vegetarian, gluten-free, dairy-free, non-veg, none)
	•	Match cuisine if provided

ChatML prompt construction is done via build_chatml_prompt(example):

<|im_start|>system
...SYSTEM_PROMPT...
<|im_end|>
<|im_start|>user
Inventory: rice, onion, lemon.
Dietary preference: gluten-free.
Cuisine: Chinese.
Request: Quick dinner using mostly my pantry.
<|im_end|>
<|im_start|>assistant

generate_single(...) then:
	•	Tokenizes the prompt
	•	Calls model.generate(...) with temperature + MAX_NEW_TOKENS
	•	Decodes only the assistant continuation and strips anything after <|im_end|>

3. Metrics
metrics.py defines how outputs are parsed and evaluated.
	•	parse_model_json(raw_text):
	•	Extracts the first JSON object from the model’s raw string
	•	Returns (parsed_json, is_valid_json)
	•	compute_example_metrics(example, parsed, valid) computes:
	•	json_valid_rate: 1.0 if valid JSON, else 0.0
	•	diet_match_rate: 1.0 if output respects the requested dietary preference, else 0.0
	•	constraint_violation_rate: 1.0 if constraints are violated, else 0.0
	•	cuisine_match_rate: 1.0 if recipe.cuisine matches requested cuisine (if any)
	•	inventory_coverage: fraction of main_ingredients that come from user_inventory
	•	aggregate_metrics(list_of_ExampleMetrics):
	•	Aggregates all per-example metrics into dataset-level means (e.g., inventory_coverage_mean).

4. Running the evaluation
From the repo root:

# Quick sanity check on a tiny subset
python -m model_development.llm_eval.run_eval \
  --max-examples 3 \
  --temperatures 0.7

# Typical benchmark run used in our analysis
python -m model_development.llm_eval.run_eval \
  --max-examples 20 \
  --temperatures 0.7

run_eval.py:
	•	Picks device (cuda → mps → cpu), uses float16 on GPU/MPS and float32 on CPU
	•	Loads tokenizer once
	•	For each model_kind in ["base", "lora"]:
	•	Loads base model, or base + LoRA adapter
	•	Evaluates for each temperature in TEMPERATURE_GRID
	•	Frees memory between models to keep MPS happy
	•	Writes:
	•	model_development/llm_eval/reports/eval_YYYYMMDD_HHMMSS.json
	•	model_development/llm_eval/reports/eval_summary_YYYYMMDD_HHMMSS.csv

Representative results (20-example run, T = 0.7):
	•	Base model base_t0.7:
	•	json_valid_rate ≈ 1.00
	•	diet_match_rate ≈ 0.43
	•	constraint_violation_rate ≈ 0.57
	•	cuisine_match_rate ≈ 1.00
	•	inventory_coverage_mean ≈ 0.70
	•	LoRA model lora_t0.7:
	•	json_valid_rate ≈ 1.00
	•	diet_match_rate ≈ 0.71
	•	constraint_violation_rate ≈ 0.29
	•	cuisine_match_rate ≈ 1.00
	•	inventory_coverage_mean ≈ 0.67

Interpretation:
	•	Both models reliably produce valid JSON with this prompt structure.
	•	The LoRA model substantially improves dietary constraint adherence and halves the constraint violation rate.
	•	Cuisine matching is already strong for both models.
	•	Inventory coverage stays high for both; small differences are expected due to randomness and synthetic data.

These results are exactly what we want for the final report: a clear, quantitative improvement from fine-tuning.

⸻

D. Bias Evaluation

Bias evaluation checks whether performance is consistent across dietary preferences and cuisines.

1. Bias dataset: val_bias.json
	•	Location: model_development/llm_eval/data/val_bias.json (logically sourced from data_pipeline/data/recipes/val_bias.json)
	•	Size: ~29 hand-crafted examples
	•	Coverage:
	•	Preferences: vegan, vegetarian, gluten-free, dairy-free, non-veg, none
	•	Cuisines: Italian, Chinese, Mexican, Indian, Japanese, Korean, American, Mediterranean, Middle Eastern, Thai, Spanish, etc.
	•	Includes tricky cases (e.g., conflicting hints in the request).

Each entry looks like:

{
  "user_inventory": ["tofu", "rice", "broccoli"],
  "preference": "vegan",
  "cuisine": "Chinese",
  "user_request": "Quick weekday dinner using mostly pantry items"
}

2. Bias evaluation script: bias_eval.py
Usage:

python -m model_development.llm_eval.bias_eval \
  --temperature 0.7 \
  --max-examples 30

What it does:
	•	Loads the bias dataset and converts it into RecipeTestExample objects (only fields present in the file are used).
	•	Evaluates both base and lora models on all examples.
	•	Computes the same metrics as in metrics.py for each example.
	•	Groups results by (model, preference, cuisine) and aggregates with aggregate_metrics.
	•	Writes a CSV to:

model_development/llm_eval/reports/bias_report.csv

Example CSV snippet (actual run):

model,preference,cuisine,n,json_valid_rate,diet_match_rate,constraint_violation_rate,cuisine_match_rate,inventory_coverage_mean
base,vegan,Chinese,1,1.0,1.0,0.0,1.0,0.75
base,gluten-free,Italian,1,0.0,,,,
...
lora,vegan,Chinese,1,1.0,1.0,0.0,1.0,0.5
lora,gluten-free,Italian,1,1.0,1.0,0.0,1.0,1.0
...

Key observations from our run:
	•	JSON validity: LoRA maintains json_valid_rate = 1.0 for all slices in this bias set. The base model fails for at least one slice (gluten-free, Italian).
	•	Dietary constraints: The base model shows violations for some vegan / dairy-free / gluten-free slices. LoRA fixes most of these so that diet_match_rate = 1.0 and constraint_violation_rate = 0.0 in the same slices.
	•	Cuisine & inventory: cuisine_match_rate is consistently 1.0 across slices for both models. inventory_coverage_mean is generally high and similar across cuisines and diets, with no obvious pattern of neglect for any specific group.

Conclusion: the LoRA-fine-tuned model is:
	•	More reliable (no JSON failures in the bias set), and
	•	More faithful to dietary constraints across cuisines.

We also explicitly document remaining edge cases (e.g., occasional difficulty for some dairy-free prompts) as limitations, rather than pretending they don’t exist.

⸻

E. Results Analysis Helper

analyze_results.py is a small helper script that:
	•	Loads the latest eval_summary_*.csv and bias_report.csv from the reports/ folder.
	•	Prints human-readable comparisons between:
	•	Base vs LoRA on the main test eval
	•	Base vs LoRA for each (preference, cuisine) slice in the bias eval

Usage:

python -m model_development.llm_eval.analyze_results

This is mainly used to copy tables / summaries into the final report and slides.

⸻

🔁 CI / Testing

We use a simple GitHub Actions workflow (e.g. .github/workflows/pantrypilot_ci.yml) to run basic checks on every push / PR.

Typical steps:
	1.	Set up Python and install dependencies
	2.	Run data pipeline tests
	3.	Run LLM eval smoke tests

Conceptually, the workflow does something like:

# Inside CI job
pip install -r data_pipeline/requirements.txt

# Data pipeline tests
pytest -q data_pipeline/tests

# LLM eval smoke test (small, to keep CI fast)
python -m model_development.llm_eval.run_eval --max-examples 1 --temperatures 0.7
python -m model_development.llm_eval.bias_eval --temperature 0.7 --max-examples 1

This ensures that:
	•	The data pipeline code is runnable and tests pass
	•	The LLM evaluation stack (imports, config, HF model loading, LoRA loading, metric computation) still works end-to-end on a tiny subset

We treat larger runs (e.g., 20 examples, full bias set) as local experiments, not CI jobs.

⸻

🧠 Reflection & Learnings (End-to-End)

From a full MLOps perspective, this project demonstrates:
	1.	Data-centric pipeline design
	•	Synthetic data generation to break the “no data” deadlock
	•	Validation, transformation, and alerting treated as first-class components
	•	DVC + GCS for reproducible datasets and lineage across team members
	2.	Model development with local + cloud resources
	•	High-volume synthetic recipe generation using Groq API
	•	Parameter-efficient fine-tuning (LoRA) of a 3B Llama model
	•	Clear separation between training repo (LoRA creation) and evaluation/pipeline repo
	3.	Robust evaluation & bias analysis
	•	Strict JSON schema enforced through prompts and metrics
	•	Automatic checks for dietary constraint adherence and cuisine correctness
	•	Custom bias slice evaluation across cuisines and dietary preferences
	4.	Practical deployment readiness
	•	Local evaluation & inference tested on CPU and Apple M3 Pro (MPS) with careful memory management
	•	Data pipeline ready to feed downstream services or endpoints
	•	CI hooks to prevent obvious regressions in both pipeline and model evaluation code

Overall, PantryPilot moves from synthetic inventory data → clean, validated tables → LLM-based recipe generation with measured behavior across multiple user segments. That matches the course goal: not just training a model, but integrating it into a reproducible, observable, and evaluable system.
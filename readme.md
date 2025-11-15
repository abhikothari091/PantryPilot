🥢 PantryPilot – Data Pipeline & Model Development

Group 16 · Personalized Grocery Forecasting & Constraint-Aware Recipe Assistant

⸻

📘 High-Level Overview

PantryPilot is a personalized grocery management and recipe recommendation system that helps users:
	•	Maintain and monitor their kitchen inventory
	•	Plan meals based on available ingredients and preferences
	•	Avoid ingredient shortages through alerts and smart suggestions

The system is composed of two major technical pillars:
	1.	Data Pipeline (this repo’s data_pipeline/)
	•	Ingestion from NeonDB (PostgreSQL)
	•	Validation with Great Expectations
	•	Transformation & feature engineering
	•	Monitoring & alerts for low-stock / expiry
	•	Data versioning with DVC + remote storage
	2.	Model Development (this repo’s model_development/)
	•	Synthetic recipe data generation & cleaning (teammate 2)
	•	LoRA fine-tuning of Llama 3.2 3B Instruct
	•	FastAPI + React app for recipe generation
	•	Local evaluation & benchmarking of base vs fine-tuned model
	•	Bias-focused slice evaluation across cuisines & dietary preferences
	•	(Assumed) CI checks for tests and formatting

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
  ├── backend/ + frontend/ (external repo) for the app
  └── llm_eval/ (this project)
        ├── run_eval.py      # Base vs LoRA evaluation
        ├── metrics.py       # Parsing and metric computation
        ├── datasets.py      # Test data loader
        ├── bias_eval.py     # Bias slice evaluation
        └── data/recipes_test.jsonl, val_bias.json

In a fully integrated version of PantryPilot, the **data pipeline outputs** would feed into the **model inference layer** to drive personalized recipe generation and inventory-aware suggestions.


⸻

🧉 Data Pipeline Components

0. Synthetic Inventory & Purchase Data

Script: data_pipeline/data/scripts/synthetic_generate.py
Goal: Generate realistic, diverse grocery data for development & testing.

Key Features:
	•	Bias mitigation: Includes both Western and Non-Western food items
	•	e.g. rice, kimchi, tofu, soy sauce, ginger, Indian spices, etc.
	•	Realistic attributes:
	•	Category (e.g., produce, dairy, pantry)
	•	Expiry dates
	•	Storage type (fridge, freezer, pantry)
	•	Nutritional tags
	•	Purchase patterns per user
	•	Configurable scale:
	•	~20 users
	•	~50–60 items per user
	•	~300 purchases per user

Outputs:
	•	data_pipeline/data/synthetic_data/pantrypilot_inventory_u20_i60_shared_ids.csv
	•	data_pipeline/data/synthetic_data/pantrypilot_purchase_u20_i60_shared_ids.csv

These synthetic CSVs are then uploaded to NeonDB and exposed as inventory and purchase_history tables.

⸻

1. Ingestion Layer

Script: data_pipeline/scripts/ingest_neon.py
Goal: Extract structured data from NeonDB and store as snapshots under data_pipeline/data/raw/.

Datasets:
	•	inventory.csv (synthetic inventory in NeonDB)
	•	purchase_history.csv (synthetic purchase history in NeonDB)
	•	cord_dataset.csv (receipt images metadata, for future OCR / VLM integration)

Output Path:
	•	data_pipeline/data/raw/

ingest_neon.py connects via SQLAlchemy using DB_URL from scripts/config.py, runs a SELECT * on each table, and writes the results as CSV snapshots.

⸻

2. Validation Layer (Great Expectations)

Script: data_pipeline/scripts/validate_data.py
Framework: Great Expectations

Purpose:
	•	Validate schema and column types
	•	Check for nulls and invalid values
	•	Enforce logical rules (e.g., expiry date after today, non-negative quantities)
	•	Generate interactive HTML quality reports

Outputs:
	•	HTML docs: data_pipeline/great_expectations/uncommitted/data_docs/local_site/index.html
	•	Summary CSV: data_pipeline/reports/validation_summary.csv

Example Outcome:

[VALIDATION] inventory.csv       → PASS ✅
[VALIDATION] purchase_history.csv → FAIL ❌ (intentional data issue for demo)

Intentional failures are left in to demonstrate how the pipeline surfaces data quality problems.

⸻

3. Transformation Layer

Scripts:
	•	data_pipeline/scripts/transform_data.py
	•	data_pipeline/scripts/utils_pint.py

Goal: Normalize all quantities and engineer useful features.

Key Steps (Inventory):
	•	Normalize units to canonical form (g, ml, pcs) using Pint via utils_pint.to_canonical.
	•	Compute stock_value = qty_canonical × unit_cost.
	•	Compute is_low_stock flag based on reorder_threshold.
	•	Write cleaned inventory to data_pipeline/data/processed/inventory_cleaned.csv.

Key Steps (Purchase History):
	•	Compute unit_price = price_total / quantity_purchased (with safe division).
	•	Write cleaned purchase history to data_pipeline/data/processed/purchase_history_cleaned.csv.

⸻

4. Monitoring & Alerts

Script: data_pipeline/scripts/update_anomalies.py
Goal: Identify low-stock or expired items and log them as alerts.

Output: data_pipeline/data/alerts/alerts.csv

Example schema:

item_name	issue_type	quantity	expiry_date
Milk	Expired	1	2025-09-15
Rice	Low Stock	0.45 kg	—

These alerts can later be wired into a UI or notification service.

⸻

5. Versioning & Reproducibility (DVC + GCS)

Tools: Git + DVC + Google Cloud Storage

Tracked folders:

data_pipeline/data/raw/
data_pipeline/data/processed/
data_pipeline/data/alerts/

Typical workflow:

# Initialize DVC
cd data_pipeline
dvc init

# Configure remote
dvc remote add -d myremote gs://pantrypilot-dvc-storage/data

git add .dvc .dvcignore

dvc add data/raw data/processed data/alerts
dvc push  # Upload to GCS

git add data/*.dvc .dvc/config
git commit -m "Track datasets with DVC and GCS remote"

Verification commands:

dvc status   # Check if local and remote are in sync
dvc pull     # Download from GCS if needed

This ensures that every pipeline run is reproducible with a specific version of the raw/processed/alerts data.

⸻

6. Orchestration with Airflow

DAG file: data_pipeline/airflow/dags/pantry_pilot_dag.py

Pipeline Flow:

ingest_neon → validate_data → transform_data → detect_anomalies → dvc_status

DAG Configuration:
	•	DAG ID: pantrypilot_data_pipeline
	•	Schedule: Currently manual; can be set to "0 6 * * *" for daily 6 AM runs.
	•	Core tasks:
	1.	ingest_neon – Extract from NeonDB
	2.	validate_data – Run Great Expectations
	3.	transform_data – Perform transformations
	4.	detect_anomalies – Generate alerts
	5.	dvc_status – Check DVC sync state

Example test run:

export AIRFLOW_HOME=$(pwd)/airflow
airflow db migrate

# Test the full DAG
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
│   │   ├── data/
│   │   │   ├── recipes_test.jsonl      # Synthetic eval set from teammate 2
│   │   │   └── val_bias.json           # Hand-crafted bias prompts
│   │   └── reports/
│   │       ├── eval_*.json
│   │       ├── eval_summary_*.csv
│   │       └── bias_report.csv
│   └── (optionally) models/            # NOT checked into git (see .gitignore)
│       └── llama3b_lambda_lora/        # LoRA adapter (local only)
│
├── DataCard/                           # Data & model documentation
├── docs/                               # Global docs (slides, notes, etc.)
├── .dvc/                               # DVC configuration
└── .gitignore                          # Includes model_development/models/

We explicitly ignore the model_development/models/ folder so that large model artifacts are not pushed to git. Instead, instructions are provided for downloading / placing them locally.

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
CI (assumed)	GitHub Actions (lint + tests)


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

Configure database:

cp .env.example .env
# Edit .env and fill in DATABASE_URL for NeonDB

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
	•	Same artifacts as manual run

⸻

🧠 Model Development: LLM Training & Evaluation

The model development work for PantryPilot focuses on recipe generation conditioned on inventory and preferences, with a strong emphasis on dietary constraint adherence and bias/coverage evaluation.

A. Synthetic Recipe Data & LoRA Fine-Tuning (Teammate 2)

This part is primarily implemented in a separate repository (RecipeGen-LLM), summarized here because our evaluation code depends on its outputs.

1. Synthetic data generation (Groq + Llama 3.1 8B)
	•	Generate ~12,000 synthetic recipes across 6 realistic scenarios:
	•	Full inventory usage
	•	Pure dietary constraints (vegan, vegetarian, gluten-free, dairy-free)
	•	Cuisine-specific (Italian, Chinese, Mexican, Indian, Japanese, Korean)
	•	Combined constraints (e.g., vegan Italian)
	•	User-requested ingredients (all present)
	•	Missing/partial match scenarios
	•	Use Groq API + Llama 3.1 8B for fast, cost-effective generation.
	•	Enforce JSON output with fields: recipe name, cuisine, culinary_preference, time, main_ingredients, steps, note, shopping_list.

2. ChatML conversion & cleaning
	•	Convert recipes into ChatML-style conversations:
	•	system: Instructions for the recipe generator
	•	user: Inventory + preference request
	•	assistant: JSON object with recipe
	•	Run validation:
	•	Check vegan, vegetarian, gluten-free, dairy-free compliance
	•	Remove recipes that violate constraints (e.g., honey in vegan, soy sauce in gluten-free)
	•	Final cleaned dataset: ~11,850 recipes.

3. LoRA fine-tuning on Lambda Labs
	•	Base model: meta-llama/Llama-3.2-3B-Instruct.
	•	Fine-tuning method: LoRA via PEFT.
	•	Typical config:
	•	Rank r = 16, alpha = 32
	•	Target modules: q_proj, k_proj, v_proj, o_proj
	•	3 epochs, AdamW, cosine LR schedule
	•	Output adapter folder (downloaded separately): models/llama3b_lambda_lora/.

This fine-tuned adapter is loaded by our llm_eval code to compare against the base model.

⸻

B. LLM Evaluation: Base vs LoRA

All LLM evaluation logic lives under model_development/llm_eval/.

1. Config & datasets
	•	config.py defines:
	•	PROJECT_ROOT: path to repo root
	•	BASE_MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
	•	LORA_ADAPTER_DIR: local path to the downloaded LoRA adapter
	•	MAX_NEW_TOKENS: generation length cap
	•	TEMPERATURE_GRID: list of temperatures to evaluate
	•	datasets.py:
	•	Defines a RecipeTestExample dataclass
	•	Implements load_recipes_test() to read recipes_test.jsonl
	•	Each test example encodes:
	•	user_inventory (list of ingredient names)
	•	preference (vegan / vegetarian / gluten-free / dairy-free / non-veg / none)
	•	cuisine
	•	user_request (optional free-text request)

2. Prompting & generation
run_eval.py provides:
	•	SYSTEM_PROMPT describing RecipeGen behavior:
	•	Always output exactly one valid JSON object, no markdown
	•	Specific schema:

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


	•	Strict rules to stop the model from exploding missing_ingredients into huge lists.

	•	build_chatml_prompt(example):
	•	Constructs a ChatML conversation:

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


	•	generate_single(...):
	•	Tokenizes the ChatML prompt
	•	Calls model.generate(...) with controlled temperature and MAX_NEW_TOKENS
	•	Strips everything after <|im_end|> in the decoded text

3. Metrics
metrics.py defines:
	•	parse_model_json(raw_text):
	•	Extract the first JSON object from the raw string
	•	Return (parsed_json, is_valid_json).
	•	compute_example_metrics(example, parsed, valid):
	•	json_valid_rate (per example: 1 if valid JSON)
	•	diet_match_rate: how often the recipe output respects the dietary preference
	•	constraint_violation_rate: fraction of outputs that violate diet rules
	•	cuisine_match_rate: how often recipe.cuisine matches expected cuisine
	•	inventory_coverage: fraction of recipe main ingredients that come from the inventory
	•	aggregate_metrics(per_example_metrics):
	•	Compute simple averages across examples to report dataset-level metrics.

4. Running the evaluation
From the repo root:

# Example: run on 20 test examples with T=0.7 on MPS or CPU
python -m model_development.llm_eval.run_eval \
  --max-examples 20 \
  --temperatures 0.7

What it does:
	•	Picks device (CUDA → MPS → CPU)
	•	Loads tokenizer once
	•	Loads base model and evaluates at each temperature
	•	Frees memory
	•	Loads base+LoRA model and evaluates at each temperature
	•	Writes:
	•	model_development/llm_eval/reports/eval_YYYYMMDD_HHMMSS.json
	•	model_development/llm_eval/reports/eval_summary_YYYYMMDD_HHMMSS.csv

Example result (20-example run, T=0.7):
	•	Base model base_t0.7:
	•	json_valid_rate: 1.0
	•	diet_match_rate: ~0.43
	•	constraint_violation_rate: ~0.57
	•	cuisine_match_rate: 1.0
	•	inventory_coverage_mean: ~0.70
	•	LoRA model lora_t0.7:
	•	json_valid_rate: 1.0
	•	diet_match_rate: ~0.71
	•	constraint_violation_rate: ~0.29
	•	cuisine_match_rate: 1.0
	•	inventory_coverage_mean: ~0.67

Interpretation:
	•	Both models reliably output valid JSON (evaluation prompt is strong enough).
	•	LoRA model significantly improves dietary constraint adherence and reduces violations.
	•	Inventory usage stays high for both models, with a minor drop for LoRA that is acceptable given better respect of constraints.

⸻

C. Bias Evaluation

Bias evaluation checks whether performance is consistent across dietary preferences and cuisines.

1. Bias dataset: val_bias.json
	•	Location: data_pipeline/data/recipes/val_bias.json
	•	Manually designed ~29 scenarios covering:
	•	Preferences: vegan, vegetarian, gluten-free, dairy-free, non-veg, none
	•	Cuisines: Italian, Chinese, Mexican, Indian, Japanese, Korean, American, Mediterranean, Middle Eastern, Thai, Spanish, etc.
	•	Mixed cases: conflicting preferences, “none” preference but explicit meat, etc.

Each entry is something like:

{
  "user_inventory": ["tofu", "rice", "broccoli"],
  "preference": "vegan",
  "cuisine": "Chinese",
  "user_request": "Quick weekday dinner using mostly pantry items"
}

2. Bias evaluation script: bias_eval.py
	•	Loads bias dataset and converts it to RecipeTestExample objects
	•	Evaluates both base and lora models at a fixed temperature (e.g., 0.7)
	•	Computes metrics for each example using the same logic as metrics.py
	•	Aggregates by slice: (model, preference, cuisine)
	•	Writes a CSV report summarizing metrics per slice.

Run:

python -m model_development.llm_eval.bias_eval \
  --temperature 0.7 \
  --max-examples 30

Output:
	•	model_development/llm_eval/reports/bias_report.csv

Example CSV snippet:

model,preference,cuisine,n,json_valid_rate,diet_match_rate,constraint_violation_rate,cuisine_match_rate,inventory_coverage_mean
base,vegan,Chinese,1,1.0,1.0,0.0,1.0,0.75
...
lora,vegan,Chinese,1,1.0,1.0,0.0,1.0,0.50
...

Observations:
	•	Both models maintain high JSON validity and high cuisine_match_rate across all slices.
	•	The LoRA model consistently achieves diet_match_rate = 1.0 for almost all slices, including stricter ones like vegan / gluten-free.
	•	The base model occasionally violates constraints in vegan / dairy-free / gluten-free slices (non-zero constraint_violation_rate).
	•	Inventory coverage remains strong and roughly similar for both models across slices.

This gives us a defensible story about fairness and robustness across cuisines and dietary preferences.

⸻

🔁 CI / Testing (Assumed Setup)

To keep things maintainable, we assume a simple CI pipeline (e.g., GitHub Actions) that runs on each push / PR:
	•	pip install -r data_pipeline/requirements.txt
	•	pytest -q data_pipeline/tests
	•	python -m model_development.llm_eval.run_eval --max-examples 1 --temperatures 0.7 (smoke test)
	•	Optional: linting (e.g., ruff or flake8)

This ensures that:
	•	The data pipeline still runs end-to-end on a small sample
	•	LLM evaluation code is at least syntactically and logically correct

(Actual CI YAML is not included here but can easily be added under .github/workflows/.)

⸻

🧠 Reflection & Learnings (End-to-End)

From a full MLOps perspective, this project demonstrates:
	1.	Data-centric pipeline design
	•	Synthetic data generation to break the “no data” deadlock
	•	Validation, transformation, and alerting as first-class citizens
	•	DVC + GCS for reproducible datasets and lineage
	2.	Model development with local + cloud resources
	•	High-volume synthetic recipe generation using Groq API
	•	Parameter-efficient fine-tuning (LoRA) on a reasonably small model (3B)
	•	Clean separation between training repo and evaluation / pipeline repo
	3.	Robust evaluation & bias analysis
	•	Structured JSON output enforced via prompts and metrics
	•	Automatic checks for dietary constraint adherence and cuisine correctness
	•	Custom bias slice evaluation across cuisines and diets
	4.	Practical deployment considerations
	•	Local evaluation & inference using MPS/CPU/GPU
	•	Data pipeline ready to feed downstream services
	•	CI hooks (assumed) to prevent regressions

Overall, PantryPilot moves from synthetic inventory data → clean, validated tables → LLM-based recipe generation with measured behavior across multiple user segments. This matches the goals of an LLMOps-style course project: not just training a model, but integrating it into a reproducible, observable, and evaluable system.
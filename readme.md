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
| Rice      | Low Stock  | 0.45 kg  | —          |

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

## 🍳 RAG Recipe Generation

**Scripts:** `recipe_endpoints.py`, `model_eval.py`
**Goal:** Generate personalized recipe recommendations using ingredient inventory with priority-based selection and local LLM inference.

### 🚀 Setup & Installation

#### Prerequisites

1. **Install Ollama**

   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # Windows
   # Download installer from https://ollama.com/download
   ```
2. **Pull the Llama model**

   ```bash
   ollama pull llama3.2:3b-instruct-q4_K_M
   ```
3. **Verify Ollama is running**

   ```bash
   # Check installed models
   ollama list

   # Test API endpoint
   curl http://localhost:11434/api/tags
   ```
5. **Start the FastAPI server**

   ```bash
   python recipe_endpoints.py
   # API runs on http://localhost:8000
   # Interactive docs at http://localhost:8000/docs
   ```

### Key Features

* **Priority-based ingredient selection:** Automatically uses older ingredients first (based on `days_in` threshold)
* **Meal-type awareness:** Adjusts recipes based on time (breakfast/lunch/dinner/snack)
* **Local LLM inference:** Uses Ollama with Llama 3.2 for privacy and speed
* **JSON-structured responses:** Standardized recipe format with name, time, ingredients, and steps

### Model Selection

* Evaluated: gemma:2b, llama3.2:3b, phi3, mistral, qwen2.5
* Selected: `llama3.2:3b-instruct-q4_K_M` for best quality/latency balance

### API Endpoints

* `POST /generate-recipes` - Main recipe generation with priority logic
* `GET /health` - Ollama connection status
* `POST /generate-recipes-custom` - Custom priority override

**Input:** `trial_inventory.txt` with 100+ items including quantities and age (`days_in`)
**Output:** JSON array of recipes prioritizing older ingredients

### Example Request/Response

```json
// Request | You can also use the sample inventory provided in the model/logs/trial_inventory.txt
{
  "inventory": [{"item": "chicken breast", "qty": "1.5kg", "days_in": 4}],
  "time": "18:30",
  "priority_threshold": 7,
  "num_recipes": 3
}

// Response
[{
  "name": "Stir-Fried Chicken",
  "time": 25,
  "main_ingredients": ["chicken breast", "bell peppers"],
  "quick_steps": "Slice chicken, stir-fry with peppers, season"
}]
```

### Troubleshooting

* **Ollama not responding:** Ensure Ollama service is running with `ollama serve`
* **Model not found:** Verify exact model name matches `llama3.2:3b-instruct-q4_K_M`
* **Port conflicts:** Ollama uses port 11434, FastAPI uses 8000 by default
* **Slow generation:** First run downloads the model (~2GB), subsequent runs are faster

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

| Category       | Tool                                   | Purpose                        |
| -------------- | -------------------------------------- | ------------------------------ |
| Database       | **NeonDB (PostgreSQL)**          | Centralized data storage       |
| Data Handling  | **pandas**, **SQLAlchemy** | ETL and transformation         |
| Validation     | **Great Expectations**           | Schema and data quality checks |
| Transformation | **Pint**                         | Unit conversions               |
| Versioning     | **Git**, **DVC**           | Code and data reproducibility  |
| Monitoring     | **Python scripts**               | Alert generation               |
| Orchestration  | **Airflow**                      | DAG automation                 |

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

| Stage          | Output                                           | Description            |
| -------------- | ------------------------------------------------ | ---------------------- |
| Ingestion      | `data_pipeline/data/raw/*.csv`                 | Raw tables from NeonDB |
| Validation     | GE HTML report                                   | Data quality summary   |
| Transformation | `data_pipeline/data/processed/*.csv`           | Standardized data      |
| Monitoring     | `data_pipeline/data/alerts/alerts.csv`         | Alerts for anomalies   |
| Logging        | `data_pipeline/reports/validation_summary.csv` | Validation status      |
| Versioning     | `.dvc` files                                   | Data lineage metadata  |

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

## 🚀 Future Enhancements

* ~~Configure DVC remote storage~~ ✅ **Completed:** Configured GCS (`gs://pantrypilot-dvc-storage/data`)
* ~~Integrate Airflow for orchestration~~ ✅ **Completed:** DAG with 5 tasks (ingest → validate → transform → anomalies → dvc)
* Deploy Airflow to cloud (Databricks, Azure ML, or Google Cloud Composer)
* Introduce APIs for real-time alerting and dashboarding
* Enhance Great Expectations suites with dynamic thresholds and schema evolution
* Set up automated DVC push/pull in CI/CD pipeline
* Add Airflow sensors for triggering on data arrival
* Implement email/Slack notifications for validation failures

---

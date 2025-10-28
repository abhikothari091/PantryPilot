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
 data/scripts/synthetic_generate.py
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
 scripts/ingest_neon.py
       │
       ▼
[Validation Layer]
 scripts/validate_data.py (Great Expectations)
       │
       ▼
[Transformation Layer]
 scripts/transform_data.py + utils_pint.py
       │
       ▼
[Monitoring & Alerts]
 scripts/update_anomalies.py
       │
       ▼
[Versioning]
 Git + DVC (raw / processed / alerts / receipts / synthetic_data)
```

---

## 🧉 Pipeline Components

### 0. Synthetic Data Generation

**Script:** `data/scripts/synthetic_generate.py`
**Goal:** Generate realistic, diverse grocery data for testing and development.

**Key Features:**
* **Bias Mitigation:** Includes both Western and Non-Western food items to prevent cultural bias in the dataset
* **Diverse Food Items:** Rice, kimchi, tofu, soy sauce, ginger, and other Asian staples alongside Western ingredients
* **Realistic Attributes:** Categories, expiry dates, storage types, nutritional tags, and purchase patterns
* **Configurable:** 20 users, 50 items per user, 300 purchases per user

**Output:**
* `data/synthetic_data/pantrypilot_inventory_u20_i60_shared_ids.csv`
* `data/synthetic_data/pantrypilot_purchase_u20_i60_shared_ids.csv`

**Upload to NeonDB:** Data is uploaded to PostgreSQL database for pipeline consumption.

---

### 1. Ingestion Layer

**Script:** `scripts/ingest_neon.py`
**Goal:** Extract structured data from NeonDB and store as snapshots in `/data/raw/`.

**Datasets:**

* `inventory.csv` (synthetic data uploaded to NeonDB)
* `purchase_history.csv` (synthetic data uploaded to NeonDB)
* `cord_dataset.csv` (receipt images dataset)

**Output Path:** `data/raw/`

---

### 2. Validation Layer

**Script:** `scripts/validate_data.py`
**Framework:** Great Expectations

**Purpose:**

* Validate schema, nulls, and logical rules
* Generate interactive HTML quality reports

**Outputs:**

* `great_expectations/uncommitted/data_docs/local_site/index.html`
* `reports/validation_summary.csv`

**Example Output:**

```
[VALIDATION] inventory.csv → PASS ✅
[VALIDATION] purchase_history.csv → FAIL ❌
```

Failures intentionally left to demonstrate detection of data issues.

---

### 3. Transformation Layer

**Scripts:** `transform_data.py`, `utils_pint.py`
**Goal:** Normalize units and engineer useful features.

**Key Steps:**

* Convert units to canonical form using **Pint** (g/ml/pcs)
* Derive: `stock_value = qty × unit_cost`, `is_low_stock` flag
* Calculate per-unit prices in purchases
* Save standardized data to `/data/processed/`

---

### 4. Monitoring & Alerts

**Script:** `scripts/update_anomalies.py`
**Purpose:** Identify low-stock or expired products and log them.

**Output:** `data/alerts/alerts.csv`

| item_name | issue_type | quantity | expiry_date |
| --------- | ---------- | -------- | ----------- |
| Milk      | Expired    | 1        | 2025-09-15  |
| Rice      | Low Stock  | 0.45 kg  | —           |

---

### 5. Versioning & Reproducibility

**Tools:** Git + DVC

**Tracked Folders:**

```
data/raw/
data/processed/
data/alerts/
```

**Commands:**

```bash
dvc init
git add .dvc .dvcignore
dvc add data/raw data/processed data/alerts
git commit -m "Track datasets with DVC"
```

**Verification:**

```
dvc status → Data and pipelines are up to date.
```

---

### 6. Orchestration (Future Scope)

The modular design supports future integration with **Prefect** or **Airflow** for automated DAG execution (Ingest → Validate → Transform → Alert) and scheduled runs on cloud environments like Databricks or Azure ML.

---

## 🧮 Folder Structure

```
PantryPilot/
├── data/
│   ├── raw.dvc                    # DVC tracked raw data
│   ├── processed.dvc              # DVC tracked processed data
│   ├── alerts.dvc                 # DVC tracked alerts
│   ├── receipts/                  # CORD receipt dataset
│   │   ├── cord_dataset/
│   │   ├── cord_dataset_with_urls.csv
│   │   └── cord_v2_dataset.csv
│   ├── scripts/
│   │   └── synthetic_generate.py  # Synthetic data generator
│   └── synthetic_data/            # Generated synthetic data
│       ├── pantrypilot_inventory_u20_i60_shared_ids.csv
│       └── pantrypilot_purchase_u20_i60_shared_ids.csv
│
├── scripts/
│   ├── ingest_neon.py            # NeonDB data ingestion
│   ├── validate_data.py          # Great Expectations validation
│   ├── transform_data.py         # Data transformation
│   ├── update_anomalies.py       # Anomaly detection
│   ├── utils_pint.py             # Unit conversion utilities
│   ├── config.py                 # Configuration settings
│   └── receipts/                 # Receipt processing scripts
│       ├── create_url_csv.py
│       ├── upload_to_gcs.sh
│       └── upload_to_neon.py
│
├── DataCard/                      # Model and data documentation
│   ├── errors-failure.pdf         # Error analysis and failure modes
│   └── user-needs.pdf             # User requirements and needs analysis
│
├── flows/                         # Prefect workflow definitions
├── great_expectations/            # GE configuration and suites
├── docs/                          # Documentation
├── .dvc/                          # DVC configuration
├── dvc.yaml                       # DVC pipeline definition
├── requirements.txt
└── readme.md
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
| Orchestration (Future) | **Prefect**                | DAG automation                 |

---

## 🧾 Running the Pipeline

### 1. Setup

```bash
git clone https://github.com/abhikothari091/PantryPilot.git
cd PantryPilot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate Synthetic Data (Optional)

```bash
python data/scripts/synthetic_generate.py
```

This generates diverse, culturally-unbiased synthetic data including both Western and Non-Western food items to prevent data bias in the model training process.

### 3. Run Pipeline Stages

```bash
python -m scripts.ingest_neon
python -m scripts.validate_data
python -m scripts.transform_data
python -m scripts.update_anomalies
```

### 4. Validate Results

* Open HTML report: `great_expectations/uncommitted/data_docs/local_site/index.html`
* Review summary: `reports/validation_summary.csv`

### 5. Check Alerts

```bash
cat data/alerts/alerts.csv
```

### 6. Verify DVC Tracking

```bash
dvc status
→ Data and pipelines are up to date.
```

---

## 📊 Outputs

| Stage          | Output                            | Description            |
| -------------- | --------------------------------- | ---------------------- |
| Ingestion      | `/data/raw/*.csv`                 | Raw tables from NeonDB |
| Validation     | GE HTML report                    | Data quality summary   |
| Transformation | `/data/processed/*.csv`           | Standardized data      |
| Monitoring     | `/data/alerts/alerts.csv`         | Alerts for anomalies   |
| Logging        | `/reports/validation_summary.csv` | Validation status      |
| Versioning     | `.dvc` files                      | Data lineage metadata  |

---

## 🧠 Reflection and Learnings

This project provided hands-on experience with designing a **real-world, production-ready data pipeline**.

**Key Learnings:**

* **Data Bias Mitigation:** Synthetic data generation includes diverse cuisines (Western and Non-Western foods) to prevent cultural bias in ML models.
* **Great Expectations:** Ensured data integrity and schema consistency through automated validation.
* **DVC:** Enabled reproducible data versioning and efficient storage tracking.
* **Modular Design:** Promotes maintainability and future scalability across pipeline components.
* **Transformation Logic:** Using Pint reinforced data standardization best practices for unit conversions.
* **Intentional Validation Failures:** Demonstrated pipeline robustness and error detection capabilities.
* **Receipt Processing:** Integrated CORD dataset for real-world receipt image processing.

This pipeline now forms the **foundation** of the larger PantryPilot system, supporting the downstream Recipe Generator and Inventory Forecaster modules.

---

## 🚀 Future Enhancements

* Integrate Prefect for automated end-to-end orchestration.
* Configure DVC remote storage (Google Drive / DagsHub).
* Introduce APIs for real-time alerting and dashboarding.
* Enhance Great Expectations suites with dynamic thresholds and schema evolution.

---

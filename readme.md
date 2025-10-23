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
Neon Database (PostgreSQL)
├── inventory
├── purchase_history
└── cord_dataset
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
 Git + DVC (raw / processed / alerts)
```

---

## 🧉 Pipeline Components

### 1. Ingestion Layer

**Script:** `scripts/ingest_neon.py`
**Goal:** Extract structured data from NeonDB and store as snapshots in `/data/raw/`.

**Datasets:**

* `inventory.csv`
* `purchase_history.csv`
* `cord_dataset.csv`

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
Data_Pipeline/
├── data/
│   ├── raw/
│   ├── processed/
│   └── alerts/
│
├── scripts/
│   ├── ingest_neon.py
│   ├── validate_data.py
│   ├── transform_data.py
│   ├── update_anomalies.py
│   └── utils_pint.py
│
├── great_expectations/
├── reports/
├── dvc.yaml
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
cd PantryPilot/Data_Pipeline
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Pipeline Stages

```bash
python -m scripts.ingest_neon
python -m scripts.validate_data
python -m scripts.transform_data
python -m scripts.update_anomalies
```

### 3. Validate Results

* Open HTML report: `great_expectations/uncommitted/data_docs/local_site/index.html`
* Review summary: `reports/validation_summary.csv`

### 4. Check Alerts

```bash
cat data/alerts/alerts.csv
```

### 5. Verify DVC Tracking

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

* Great Expectations helped ensure data integrity and schema consistency.
* DVC enabled reproducible data versioning and efficient storage.
* Modular design promotes maintainability and future scalability.
* Transformation logic (using Pint) reinforced data standardization best practices.
* Building validations that fail intentionally helped demonstrate pipeline robustness.

This pipeline now forms the **foundation** of the larger PantryPilot system, supporting the downstream Recipe Generator and Inventory Forecaster modules.

---

## 🚀 Future Enhancements

* Integrate Prefect for automated end-to-end orchestration.
* Configure DVC remote storage (Google Drive / DagsHub).
* Introduce APIs for real-time alerting and dashboarding.
* Enhance Great Expectations suites with dynamic thresholds and schema evolution.

---

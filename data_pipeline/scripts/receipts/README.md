# Receipt Data Processing Scripts

This module contains scripts for processing CORD (Consolidated Receipt Dataset) data and uploading to cloud storage and database.

## Scripts

### 1. `upload_to_gcs.sh`
Upload CORD dataset images to Google Cloud Storage.

**Usage:**
```bash
./upload_to_gcs.sh <bucket-name>
```

**Example:**
```bash
./upload_to_gcs.sh my-cord-dataset-bucket
```

**What it does:**
- Creates a GCS bucket in `us-east1` region
- Uploads train images (800 files)
- Uploads validation images (100 files)
- Sets public read permissions

### 2. `create_url_csv.py`
Generate a CSV file mapping GCS URLs to ground truth data.

**Usage:**
```bash
python3 create_url_csv.py <bucket-name>
```

**Example:**
```bash
python3 create_url_csv.py my-cord-dataset-bucket
```

**What it does:**
- Reads train and validation CSV files
- Creates img_url fields pointing to GCS
- Combines into a single CSV: `cord_dataset_with_urls.csv`

### 3. `upload_to_neon.py`
Upload the URL-mapped data to Neon PostgreSQL database.

**Usage:**
```bash
python3 upload_to_neon.py "<connection-string>"
```

**Example:**
```bash
python3 upload_to_neon.py "postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require"
```

**What it does:**
- Creates `cord_dataset` table if not exists
- Inserts (img_url, ground_truth, split, filename) records
- Stores ground_truth as JSONB for efficient querying

## Workflow

1. **Upload images to GCS:**
   ```bash
   cd /path/to/PantryPilot
   ./scripts/receipts/upload_to_gcs.sh my-bucket-name
   ```

2. **Generate URL CSV:**
   ```bash
   python3 scripts/receipts/create_url_csv.py my-bucket-name
   ```

3. **Upload to Neon:**
   ```bash
   python3 scripts/receipts/upload_to_neon.py "postgresql://..."
   ```

## Data Location

- **Images**: `data/receipts/cord_dataset/`
  - `train/` - 800 training images
  - `validation/` - 100 validation images
- **CSV files**: `data/receipts/`
  - `cord_v2_dataset.csv` - Original dataset
  - `cord_dataset_with_urls.csv` - Generated with GCS URLs

## Database Schema

```sql
CREATE TABLE cord_dataset (
    id SERIAL PRIMARY KEY,
    img_url TEXT NOT NULL,
    ground_truth JSONB NOT NULL,
    split VARCHAR(20) NOT NULL,
    filename VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Requirements

- Google Cloud SDK (for `gsutil`)
- Python packages: `pandas`, `psycopg2-binary`
- Neon PostgreSQL connection string

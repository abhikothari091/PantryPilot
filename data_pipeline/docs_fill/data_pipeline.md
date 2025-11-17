# Data Pipeline Documentation

## Overview

This document describes the data pipeline for preparing the CORD (Consolidated Receipt Dataset) for PantryPilot project. The pipeline processes receipt images and their ground truth labels, uploads them to Google Cloud Storage (GCS), and stores metadata in Neon PostgreSQL.

## Pipeline Architecture

```
CORD Dataset (Local)
    ├── Receipt Images (900 images)
    └── Ground Truth Labels (JSON)
            ↓
    Upload to GCS
            ↓
    Generate Image URLs
            ↓
    Upload to Neon PostgreSQL
    (img_url + ground_truth)
```

## Components

### 1. Dataset Structure

The CORD dataset contains:
- **Train split**: 800 receipt images
- **Validation split**: 100 receipt images
- **Ground truth**: JSON labels with OCR annotations

### 2. Scripts

#### `upload_to_gcs.sh`
Uploads receipt images to Google Cloud Storage with public read access.

**Usage:**
```bash
cd data/scripts
./upload_to_gcs.sh <bucket-name>
```

**What it does:**
1. Creates GCS bucket in `us-east1` region
2. Uploads train images (800 files) to `gs://<bucket>/train/`
3. Uploads validation images (100 files) to `gs://<bucket>/validation/`
4. Sets public read permissions for all uploaded files

**Output:**
- Public URLs: `https://storage.googleapis.com/<bucket>/{train|validation}/<filename>`

---

#### `create_url_csv.py`
Creates a CSV file mapping image URLs to ground truth labels.

**Usage:**
```bash
python3 create_url_csv.py <bucket-name>
```

**Input:**
- `cord_dataset/train_data.csv`
- `cord_dataset/validation_data.csv`

**Output:**
- `cord_dataset_with_urls.csv` with columns:
  - `img_url`: GCS public URL
  - `ground_truth`: JSON label
  - `split`: train/validation
  - `filename`: original filename

---

#### `upload_to_neon.py`
Uploads the URL-to-label mapping to Neon PostgreSQL database.

**Usage:**
```bash
python3 upload_to_neon.py "<neon-connection-string>"
```

**Database Schema:**
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

**What it does:**
1. Reads `cord_dataset_with_urls.csv`
2. Connects to Neon PostgreSQL
3. Creates table if not exists
4. Batch inserts all records
5. Validates data integrity

---

## Complete Workflow

### Prerequisites

1. **CORD Dataset**: Download from [CORD official source](https://github.com/clovaai/cord)
2. **Google Cloud**: GCS bucket with public access enabled
3. **Neon PostgreSQL**: Database instance created
4. **Python Dependencies**: Install from `requirements.txt`

```bash
pip install -r requirements.txt
```

### Step-by-Step Execution

```bash
# 1. Upload images to GCS
cd data/scripts
./upload_to_gcs.sh my-pantrypilot-bucket

# 2. Generate URL mapping CSV
python3 create_url_csv.py my-pantrypilot-bucket

# 3. Upload to Neon PostgreSQL
python3 upload_to_neon.py "postgresql://user:password@host/dbname?sslmode=require"
```

### Verification

Query the database to verify:
```sql
-- Check total records
SELECT COUNT(*) FROM cord_dataset;
-- Expected: 900 rows

-- Check split distribution
SELECT split, COUNT(*) FROM cord_dataset GROUP BY split;
-- Expected: train=800, validation=100

-- Sample query
SELECT img_url, split, filename FROM cord_dataset LIMIT 5;
```

## Data Schema

### CSV Format
```csv
img_url,ground_truth,split,filename
https://storage.googleapis.com/bucket/train/image001.png,"{\"key\": \"value\"}",train,image001.png
```

### PostgreSQL JSONB Format
```json
{
  "valid_line": [
    {
      "words": [...],
      "category": "menu.item.name"
    }
  ],
  "meta": {...}
}
```

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp config/.env.example config/.env
```

Edit `config/.env`:
```env
NEON_CONNECTION_STRING=postgresql://user:password@ep-xxx.aws.neon.tech/dbname?sslmode=require
GCS_BUCKET_NAME=my-pantrypilot-bucket
```

## Troubleshooting

### GCS Upload Issues
- Ensure `gsutil` is installed and authenticated: `gcloud auth login`
- Check bucket permissions and region settings

### Neon Connection Issues
- Verify connection string format
- Ensure SSL mode is set to `require`
- Check firewall/network settings

### Data Validation
- Verify CSV has 900 rows (800 train + 100 validation)
- Check JSON formatting in ground_truth column
- Ensure all image URLs are publicly accessible

## Next Steps

After completing the data pipeline:
1. Verify all images are accessible via URLs
2. Test database queries for model training
3. Implement data loading pipeline for ML model
4. Set up monitoring for data quality

## References

- [CORD Dataset Paper](https://openreview.net/forum?id=SJl3z659UH)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Neon PostgreSQL Documentation](https://neon.tech/docs)

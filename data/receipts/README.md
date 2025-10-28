# CORD Receipt Dataset

This directory contains the CORD (Consolidated Receipt Dataset) for receipt OCR and information extraction.

## Dataset Structure

```
receipts/
├── cord_dataset/
│   ├── train/              # 800 training images
│   │   └── train_*.png
│   ├── validation/         # 100 validation images
│   │   └── validation_*.png
│   ├── train_data.csv      # Training ground truth
│   └── validation_data.csv # Validation ground truth
├── cord_v2_dataset.csv     # Combined original dataset
└── cord_dataset_with_urls.csv  # Dataset with GCS URLs (generated)
```

## Dataset Details

- **Total Images**: 900 (800 train + 100 validation)
- **Format**: PNG images
- **Ground Truth**: JSON format containing receipt fields
  - Store name
  - Items and prices
  - Total amount
  - Date, etc.

## CSV Files

### `cord_v2_dataset.csv`
Original dataset with local file paths.

### `cord_dataset_with_urls.csv`
Generated file with GCS public URLs. Created by:
```bash
python3 ../../scripts/receipts/create_url_csv.py <bucket-name>
```

**Columns:**
- `img_url`: Public GCS URL
- `ground_truth`: JSON string with receipt data
- `split`: 'train' or 'validation'
- `filename`: Original filename

## Usage

1. **Upload to GCS**: See [../../scripts/receipts/README.md](../../scripts/receipts/README.md)
2. **Generate URLs**: Run `create_url_csv.py`
3. **Upload to Database**: Run `upload_to_neon.py`

## Ground Truth Format

Each ground_truth entry is a JSON object with receipt information:
```json
{
  "store_name": "...",
  "items": [...],
  "total": "...",
  "date": "...",
  ...
}
```

## Notes

- Images are large (~1MB each), so they're stored separately in GCS
- Only metadata and URLs are stored in the database
- Use DVC if version controlling this data

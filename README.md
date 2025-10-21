# PantryPilot

A collaborative MLOps project for intelligent receipt processing and pantry management.

## Project Overview

PantryPilot uses machine learning to extract structured information from receipt images, helping users track their pantry inventory automatically.

## Current Status

### Completed: Data Pipeline Setup

We have successfully set up the data infrastructure using the CORD (Consolidated Receipt Dataset):

- **Dataset**: 900 receipt images with ground truth labels
  - Training set: 800 images
  - Validation set: 100 images
- **Storage**: Images hosted on Google Cloud Storage with public URLs
- **Database**: Metadata stored in Neon PostgreSQL (image URLs + ground truth labels)

## Project Structure

```
PantryPilot/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   └── scripts/           # Data pipeline scripts
│       ├── upload_to_gcs.sh
│       ├── create_url_csv.py
│       └── upload_to_neon.py
├── docs/
│   └── data_pipeline.md   # Detailed pipeline documentation
└── config/
    └── .env.example       # Environment variables template
```

## Getting Started

### Prerequisites

- Python 3.8+
- Google Cloud SDK (for GCS operations)
- Neon PostgreSQL account
- CORD Dataset ([download here](https://github.com/clovaai/cord))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/abhikothari091/PantryPilot.git
   cd PantryPilot
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your credentials
   ```

### Data Pipeline Setup

For detailed instructions on setting up the data pipeline, see [Data Pipeline Documentation](docs/data_pipeline.md).

**Quick Start:**

```bash
# 1. Upload images to Google Cloud Storage
cd data/scripts
./upload_to_gcs.sh your-bucket-name

# 2. Generate URL mapping CSV
python3 create_url_csv.py your-bucket-name

# 3. Upload to Neon PostgreSQL
python3 upload_to_neon.py "postgresql://user:password@host/dbname?sslmode=require"
```

## Technology Stack

### Data Infrastructure
- **Cloud Storage**: Google Cloud Storage (GCS)
- **Database**: Neon PostgreSQL (serverless)
- **Dataset**: CORD (Consolidated Receipt Dataset)

### Python Libraries
- `pandas`: Data manipulation
- `psycopg2`: PostgreSQL adapter
- `google-cloud-storage`: GCS client

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

## Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

## Roadmap

- [x] Data pipeline setup
- [x] CORD dataset upload to GCS
- [x] Metadata storage in Neon PostgreSQL
- [ ] Model training pipeline
- [ ] Receipt OCR inference API
- [ ] Pantry inventory tracking
- [ ] Web/mobile interface
- [ ] Deployment on cloud platform

## Dataset

This project uses the **CORD (Consolidated Receipt Dataset)** for training:
- 900+ receipt images with structured annotations
- Multi-language support
- Real-world receipt variations
- Rich ground truth labels (items, prices, totals, etc.)

**Citation:**
```
Park, S., Shin, S., Lee, B., Lee, J., Surh, J., Seo, M., & Lee, H. (2019).
CORD: A Consolidated Receipt Dataset for Post-OCR Parsing.
Workshop on Document Intelligence at NeurIPS 2019.
```

## License

[Add your license here]

## Contact

For questions or collaboration opportunities:
- Repository: https://github.com/abhikothari091/PantryPilot
- Issues: https://github.com/abhikothari091/PantryPilot/issues

## Acknowledgments

- CORD Dataset creators
- Google Cloud Platform
- Neon PostgreSQL team

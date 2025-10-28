#!/bin/bash

# GCS 업로드 스크립트
# 사용법: ./upload_to_gcs.sh <bucket-name>

if [ -z "$1" ]; then
    echo "Usage: ./upload_to_gcs.sh <bucket-name>"
    echo "Example: ./upload_to_gcs.sh my-cord-dataset-bucket"
    exit 1
fi

BUCKET_NAME=$1
REGION="us-east1"  # 무료 티어 region (Boston에 가장 가까움)

echo "================================================"
echo "GCS 버킷 설정 및 업로드"
echo "================================================"
echo "Bucket name: $BUCKET_NAME"
echo "Region: $REGION"
echo ""

# 1. 버킷 생성 (이미 있으면 에러 무시)
echo "[1/4] Creating GCS bucket..."
gsutil mb -l $REGION gs://$BUCKET_NAME 2>/dev/null || echo "Bucket already exists or error occurred"

# 2. 이미지 업로드
echo ""
echo "[2/4] Uploading train images (800 files)..."
gsutil -m cp -r cord_dataset/train/* gs://$BUCKET_NAME/train/

echo ""
echo "[3/4] Uploading validation images (100 files)..."
gsutil -m cp -r cord_dataset/validation/* gs://$BUCKET_NAME/validation/

# 3. Public 읽기 권한 부여
echo ""
echo "[4/4] Setting public read permissions..."
gsutil -m acl ch -r -u AllUsers:R gs://$BUCKET_NAME/train
gsutil -m acl ch -r -u AllUsers:R gs://$BUCKET_NAME/validation

echo ""
echo "================================================"
echo "✓ Upload completed!"
echo "================================================"
echo ""
echo "Public URLs will be:"
echo "  Train: https://storage.googleapis.com/$BUCKET_NAME/train/<filename>"
echo "  Validation: https://storage.googleapis.com/$BUCKET_NAME/validation/<filename>"
echo ""
echo "Next steps:"
echo "  1. Run: python3 create_url_csv.py $BUCKET_NAME"
echo "  2. Upload to Neon PostgreSQL"

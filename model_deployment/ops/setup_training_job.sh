#!/bin/bash
set -e

# Configuration
PROJECT_ID="mlops-compute-lab"
REGION="us-central1"
JOB_NAME="pantrypilot-training-job"
REPO_NAME="pantrypilot"
IMAGE_NAME="pantrypilot-training"
IMAGE_TAG="latest"
ARTIFACT_REGISTRY_HOST="${REGION}-docker.pkg.dev"
IMAGE_URI="${ARTIFACT_REGISTRY_HOST}/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "🚀 Setting up Cloud Run Training Job for Project: $PROJECT_ID"

# 1. Enable Cloud Run (if not already)
echo " [1/3] Enabling APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com --project $PROJECT_ID

# 2. Build and Push Training Image
echo " [2/3] Building Training Image..."
gcloud auth configure-docker $ARTIFACT_REGISTRY_HOST --quiet

# Navigate to project root
cd "$(dirname "$0")/../.."

# Build
docker build --platform linux/amd64 -t $IMAGE_URI -f model_development/Dockerfile.training .

# Push
docker push $IMAGE_URI

# 3. Create Cloud Run Job
echo " [3/3] Creating Cloud Run Job definition..."

# Note: We set generic env vars here. Sensitive ones (DB_URL) should be passed at execution time or managed via Secret Manager.
# For simplicity in this demo, we assume DB_URL is safe or env var injection is handled by the triggering script.

gcloud run jobs create $JOB_NAME \
    --image $IMAGE_URI \
    --region $REGION \
    --tasks 1 \
    --parallelism 1 \
    --cpu 4 \
    --memory 16Gi \
    --project $PROJECT_ID \
    --task-timeout 3600s \
    --set-env-vars=GCS_BUCKET_NAME="gs://${PROJECT_ID}-models/llama3b_lambda_lora" \
    --command python3 \
    --args cloud_train_entrypoint.py

# Note on GPU:
# Cloud Run Jobs GEN2 supports GPUs. We need to specify it.
# Currently gcloud CLI support for GPU in Jobs might require beta or specific flags.
# We will try adding the annotation via beta.

echo "    Updating Job with GPU configuration (nvidia-l4)..."
gcloud beta run jobs update $JOB_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --set-resources-limits=nvidia.com/gpu=1 \
    --gpu-type=nvidia-l4

echo "✅ Training Job Setup Complete!"
echo "   Job Name: $JOB_NAME"
echo "   Image: $IMAGE_URI"

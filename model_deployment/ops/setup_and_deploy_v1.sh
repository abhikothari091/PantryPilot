#!/bin/bash
set -e

# Configuration
PROJECT_ID="mlops-compute-lab"
REGION="us-central1"
SERVICE_NAME="pantrypilot-llm-v2"
REPO_NAME="pantrypilot"
IMAGE_NAME="pantrypilot-llm"
IMAGE_TAG="latest"
BUCKET_NAME="${PROJECT_ID}-models"
ARTIFACT_REGISTRY_HOST="${REGION}-docker.pkg.dev"
IMAGE_URI="${ARTIFACT_REGISTRY_HOST}/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "🚀 Starting Initial Setup for Project: $PROJECT_ID"

# 1. Enable Required APIs
echo " [1/5] Enabling required GCP Services..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com compute.googleapis.com cloudbuild.googleapis.com storage.googleapis.com --project $PROJECT_ID

# 2. Create GCS Bucket for Models (if not exists)
echo " [2/5] Checking GCS Bucket..."
if ! gcloud storage buckets describe gs://$BUCKET_NAME &>/dev/null; then
    echo "    Creating bucket 'gs://$BUCKET_NAME'..."
    gcloud storage buckets create gs://$BUCKET_NAME --project=$PROJECT_ID --location=$REGION
else
    echo "    Bucket 'gs://$BUCKET_NAME' already exists."
fi

# 3. Create Artifact Registry Repository (if not exists)
echo " [3/5] Checking Artifact Registry..."
if ! gcloud artifacts repositories describe $REPO_NAME --location=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "    Creating repository '$REPO_NAME'..."
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --project=$PROJECT_ID \
        --description="Docker repository for PantryPilot"
else
    echo "    Repository '$REPO_NAME' already exists."
fi

# 4. Build and Push Docker Image
echo " [4/5] Build and Push Docker Image..."
# Authenticate Docker to Artifact Registry
gcloud auth configure-docker $ARTIFACT_REGISTRY_HOST --quiet
# ... (rest of build logic)
# Switch context to project root
cd "$(dirname "$0")/../.."

# Build
echo "    Building container..."
docker build --platform linux/amd64 -t $IMAGE_URI -f model_deployment/cr_backend/Dockerfile model_deployment/cr_backend

# Push
echo "    Pushing container to $IMAGE_URI..."
docker push $IMAGE_URI

# 5. Deploy to Cloud Run with GPU
echo " [5/5] Deploying to Cloud Run (GPU + Extended Timeout)..."
gcloud beta run deploy $SERVICE_NAME \
    --image=$IMAGE_URI \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --cpu=4 \
    --memory=16Gi \
    --gpu=1 \
    --gpu-type=nvidia-l4 \
    --timeout=900 \
    --port=7860 \
    --min-instances=0 \
    --max-instances=1 \
    --project=$PROJECT_ID \
    --set-env-vars=LAST_MODEL_UPDATE="$(date)",GCS_BUCKET_NAME="$BUCKET_NAME",HF_TOKEN="$HF_TOKEN" \
    --update-annotations=run.googleapis.com/gpu-zonal-redundancy=false \
    --cpu-boost

echo "✅ Initial Deployment Complete!"
echo "   Service URL: $(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')"

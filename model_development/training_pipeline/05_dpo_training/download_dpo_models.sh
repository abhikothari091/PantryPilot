#!/bin/bash

##
# Download DPO models from GCS
# Usage: ./download_dpo_models.sh [persona_id]
#   If persona_id is not specified, downloads all models
##

set -e

GCS_BUCKET="gs://pantrypilot-dpo-models"
VERSION="v1.0"
OUTPUT_DIR="./trained_models"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Persona list
PERSONAS=(
    "persona_a_korean_spicy"
    "persona_b_indian_veg"
    "persona_c_italian_gf"
    "persona_d_japanese_lowsodium"
    "persona_e_mexican_vegan"
    "persona_f_chinese_keto"
)

download_model() {
    local persona=$1
    local model_path="${GCS_BUCKET}/${VERSION}/${persona}_${VERSION}/"
    local output_path="${OUTPUT_DIR}/${persona}_${VERSION}"

    echo "📥 Downloading ${persona}..."

    if gcloud storage cp -r "$model_path" "$output_path"; then
        echo "✅ Downloaded ${persona} to ${output_path}"
    else
        echo "❌ Failed to download ${persona}"
        return 1
    fi
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Download specific persona or all
if [ $# -eq 1 ]; then
    PERSONA_ID=$1
    echo "Downloading single persona: ${PERSONA_ID}"
    download_model "$PERSONA_ID"
else
    echo "Downloading all DPO models..."
    for persona in "${PERSONAS[@]}"; do
        download_model "$persona"
    done
    echo ""
    echo "🎉 All models downloaded successfully!"
fi

echo ""
echo "Models saved to: ${OUTPUT_DIR}"
echo "Total size:"
du -sh "$OUTPUT_DIR"

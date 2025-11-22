#!/bin/bash

# Lambda Labs에서 실행할 전체 페르소나 DPO 학습 스크립트

export BASE_MODEL="meta-llama/Llama-3.2-3B-Instruct"
export ADAPTER_PATH="../../models/llama3b_lambda_lora"
export DATA_DIR="../../data/dpo_training_data"
export OUTPUT_DIR="../../models/dpo_personas"

PERSONAS=(
    "persona_a_korean_spicy"
    "persona_b_indian_veg"
    "persona_c_italian_gf"
    "persona_d_japanese_lowsodium"
    "persona_e_mexican_vegan"
    "persona_f_chinese_keto"
)

echo "=========================================="
echo "DPO Training for All Personas"
echo "=========================================="
echo ""
echo "Base Model: $BASE_MODEL"
echo "Adapter: $ADAPTER_PATH"
echo "Data Directory: $DATA_DIR"
echo "Output Directory: $OUTPUT_DIR"
echo ""
echo "Personas to train: ${#PERSONAS[@]}"
echo "=========================================="
echo ""

for PERSONA in "${PERSONAS[@]}"; do
    echo "=========================================="
    echo "Training persona: $PERSONA"
    echo "=========================================="

    python train_dpo.py \
        --persona $PERSONA \
        --base_model $BASE_MODEL \
        --adapter $ADAPTER_PATH \
        --data_dir $DATA_DIR \
        --output_dir $OUTPUT_DIR

    if [ $? -eq 0 ]; then
        echo "✅ Completed: $PERSONA"
    else
        echo "❌ Failed: $PERSONA"
    fi
    echo ""
done

echo "=========================================="
echo "🎉 All persona training complete!"
echo "=========================================="

"""
DPO (Direct Preference Optimization) 학습 스크립트
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel, LoraConfig, get_peft_model
from trl import DPOTrainer, DPOConfig
from datasets import load_dataset
import yaml
import argparse
from pathlib import Path


def train_dpo_persona(
    base_model_path: str,
    adapter_path: str,
    persona_id: str,
    train_file: str,
    output_dir: str
):
    """
    페르소나별 DPO 학습
    """
    print(f"\n{'='*60}")
    print(f"Training DPO model for: {persona_id}")
    print(f"{'='*60}\n")

    # 1. 모델 로드 (기존 fine-tuned 모델 사용)
    print("Loading base model and adapter...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path)
    tokenizer.pad_token = tokenizer.eos_token

    # 4-bit 양자화 설정
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        device_map={"": 0}  # 모든 레이어를 GPU 0에 배치
    )

    # 기존 LoRA adapter 로드
    model = PeftModel.from_pretrained(base_model, adapter_path)

    # LoRA 파라미터를 학습 가능하게 설정
    model.print_trainable_parameters()  # 디버깅용
    for name, param in model.named_parameters():
        if 'lora' in name.lower():
            param.requires_grad = True

    # 2. 데이터셋 로드
    print(f"Loading dataset from {train_file}...")
    dataset = load_dataset('json', data_files=train_file, split='train')

    # 80/20 train/eval split
    dataset = dataset.train_test_split(test_size=0.2, seed=42)

    print(f"Train samples: {len(dataset['train'])}")
    print(f"Eval samples: {len(dataset['test'])}")

    # 3. DPO 학습 설정
    training_args = DPOConfig(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,  # Reduced for L4 GPU memory
        per_device_eval_batch_size=1,   # Reduced for L4 GPU memory
        gradient_accumulation_steps=8,  # Effective batch = 8

        learning_rate=5e-5,  # DPO는 일반적으로 낮은 LR
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",

        bf16=True,  # L4/A100은 BF16 native 지원
        gradient_checkpointing=True,  # Enable to save memory
        gradient_checkpointing_kwargs={"use_reentrant": False},  # Required for DPO
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,

        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,

        report_to="none",  # MLflow 연동 시 변경
        max_length=512,  # Limit sequence length to save memory
        max_prompt_length=256,
    )

    # 4. DPO Trainer 초기화
    print("Initializing DPO Trainer...")
    dpo_trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset['train'],
        eval_dataset=dataset['test'],
        processing_class=tokenizer,  # 최신 버전에서는 tokenizer 대신 processing_class 사용
    )

    # 5. 학습 실행
    print("\n🚀 Starting DPO training...\n")
    dpo_trainer.train()

    # 6. 모델 저장
    print(f"\n💾 Saving model to {output_dir}...")
    dpo_trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"\n✅ Training complete for {persona_id}!")

    return model


def main():
    parser = argparse.ArgumentParser(description="Train DPO model for a persona")
    parser.add_argument("--persona", type=str, required=True, help="Persona ID")
    parser.add_argument("--base_model", type=str, default="meta-llama/Llama-3.2-3B-Instruct")
    parser.add_argument("--adapter", type=str, default="../../models/llama3b_lambda_lora")
    parser.add_argument("--data_dir", type=str, default="../../data/dpo_training_data")
    parser.add_argument("--output_dir", type=str, default="../../models/dpo_personas")
    args = parser.parse_args()

    # 학습 데이터 파일
    train_file = f"{args.data_dir}/{args.persona}_dpo_train.jsonl"

    if not Path(train_file).exists():
        print(f"Error: Training file not found: {train_file}")
        return

    # 출력 디렉토리
    output_dir = f"{args.output_dir}/{args.persona}_v1.0"

    # DPO 학습 실행
    train_dpo_persona(
        base_model_path=args.base_model,
        adapter_path=args.adapter,
        persona_id=args.persona,
        train_file=train_file,
        output_dir=output_dir
    )


if __name__ == "__main__":
    main()

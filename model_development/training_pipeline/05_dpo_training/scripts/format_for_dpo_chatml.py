"""
ChatML DPO 페어를 학습 데이터로 변환
"""

import json
from pathlib import Path
import argparse


def format_for_dpo_training(input_dir: Path, output_dir: Path):
    """
    GPT-4 평가 완료된 페어를 DPO 학습용으로 변환

    Input format:
    {
      "prompt": "<|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n",
      "chosen": "{JSON recipe}",
      "rejected": "{JSON recipe}",
      "metadata": {...}
    }

    Output format (DPO 표준):
    {
      "prompt": "...",
      "chosen": "...",
      "rejected": "...",
    }
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    all_pairs = []
    persona_pairs = {}

    # 모든 페르소나의 final pairs 로드
    for input_file in input_dir.glob("*_dpo_pairs.jsonl"):
        print(f"\nLoading {input_file.name}...")

        with open(input_file, encoding='utf-8') as f:
            for line in f:
                pair = json.loads(line)

                # DPO 학습 형식 (간단하게)
                dpo_pair = {
                    "prompt": pair['prompt'],  # ChatML prompt (system + user + <|im_start|>assistant)
                    "chosen": pair['chosen'],  # JSON recipe string
                    "rejected": pair['rejected'],  # JSON recipe string
                    # Metadata는 선택사항 (학습에 직접 사용 안 함)
                }

                all_pairs.append(dpo_pair)

                # 페르소나별 분류
                persona = pair['metadata']['persona']
                if persona not in persona_pairs:
                    persona_pairs[persona] = []
                persona_pairs[persona].append(dpo_pair)

    if not all_pairs:
        print("\nWarning: No DPO pairs found in input directory")
        return

    # 페르소나별 저장
    for persona_id, pairs in persona_pairs.items():
        output_file = output_dir / f"{persona_id}_dpo_train.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + '\n')

        print(f"✅ {persona_id}: {len(pairs)} pairs → {output_file.name}")

    # 전체 통합 (all personas)
    all_output = output_dir / "all_personas_dpo_train.jsonl"
    with open(all_output, 'w', encoding='utf-8') as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"\n✅ Total: {len(all_pairs)} pairs → {all_output.name}")

    # 통계
    print(f"\n{'='*60}")
    print("Dataset Statistics:")
    print(f"{'='*60}")
    for persona_id, pairs in persona_pairs.items():
        print(f"  {persona_id}: {len(pairs)} pairs")
    print(f"{'='*60}")
    print(f"  Total: {len(all_pairs)} pairs")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Format DPO pairs for training")
    parser.add_argument("--input_dir", default="../../data/dpo_final_pairs",
                       help="Input directory with DPO pairs")
    parser.add_argument("--output_dir", default="../../data/dpo_training_data",
                       help="Output directory for training data")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    print(f"Formatting DPO pairs from {input_dir}")
    print(f"Output to {output_dir}\n")

    format_for_dpo_training(input_dir, output_dir)

    print("\n🎉 Formatting complete!")


if __name__ == "__main__":
    main()

"""
GCS URL과 ground_truth를 매핑한 CSV 생성 스크립트
"""
import pandas as pd
import sys

def create_url_csv(bucket_name):
    """GCS 버킷명을 받아서 img_url과 ground_truth를 매핑한 CSV 생성"""

    print(f"Creating CSV with GCS URLs for bucket: {bucket_name}")
    print("="*60)

    # Train 데이터 처리
    print("\n[1/2] Processing train data...")
    train_df = pd.read_csv('cord_dataset/train_data.csv')
    train_df['img_url'] = train_df['filename'].apply(
        lambda x: f"https://storage.googleapis.com/{bucket_name}/train/{x}"
    )
    train_df['split'] = 'train'

    # Validation 데이터 처리
    print("[2/2] Processing validation data...")
    val_df = pd.read_csv('cord_dataset/validation_data.csv')
    val_df['img_url'] = val_df['filename'].apply(
        lambda x: f"https://storage.googleapis.com/{bucket_name}/validation/{x}"
    )
    val_df['split'] = 'validation'

    # 결합 및 필요한 컬럼만 선택
    final_df = pd.concat([train_df, val_df], ignore_index=True)
    final_df = final_df[['img_url', 'ground_truth', 'split', 'filename']]

    # CSV 저장
    output_file = 'cord_dataset_with_urls.csv'
    final_df.to_csv(output_file, index=False)

    print(f"\n✓ CSV created: {output_file}")
    print(f"  Total rows: {len(final_df)}")
    print(f"  Train: {len(train_df)}")
    print(f"  Validation: {len(val_df)}")

    print("\nPreview:")
    print(final_df.head())

    return output_file

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 create_url_csv.py <bucket-name>")
        print("Example: python3 create_url_csv.py my-cord-dataset-bucket")
        sys.exit(1)

    bucket_name = sys.argv[1]
    create_url_csv(bucket_name)

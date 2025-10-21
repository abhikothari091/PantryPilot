"""
Neon PostgreSQL에 (img_url, ground_truth) 데이터 업로드 스크립트
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import json

def upload_to_neon(connection_string, csv_file='cord_dataset_with_urls.csv'):
    """
    Neon PostgreSQL에 데이터 업로드

    Args:
        connection_string: Neon 연결 문자열
            예: "postgresql://user:password@host/dbname?sslmode=require"
        csv_file: URL이 포함된 CSV 파일 경로
    """

    print("="*60)
    print("Uploading to Neon PostgreSQL")
    print("="*60)

    # CSV 읽기
    print(f"\n[1/4] Reading CSV: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"  Total rows: {len(df)}")

    # DB 연결
    print("\n[2/4] Connecting to Neon PostgreSQL...")
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        print("  ✓ Connected successfully")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return

    # 테이블 생성
    print("\n[3/4] Creating table if not exists...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cord_dataset (
            id SERIAL PRIMARY KEY,
            img_url TEXT NOT NULL,
            ground_truth JSONB NOT NULL,
            split VARCHAR(20) NOT NULL,
            filename VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("  ✓ Table ready")

    # 데이터 삽입
    print("\n[4/4] Inserting data...")
    data_to_insert = []
    for _, row in df.iterrows():
        # ground_truth를 JSON으로 파싱 (이미 JSON 문자열이므로)
        data_to_insert.append((
            row['img_url'],
            row['ground_truth'],  # JSONB로 자동 변환됨
            row['split'],
            row['filename']
        ))

    # Batch insert for better performance
    execute_values(
        cur,
        """
        INSERT INTO cord_dataset (img_url, ground_truth, split, filename)
        VALUES %s
        """,
        data_to_insert,
        template="(%s, %s::jsonb, %s, %s)"
    )

    conn.commit()
    print(f"  ✓ Inserted {len(data_to_insert)} rows")

    # 검증
    cur.execute("SELECT COUNT(*) FROM cord_dataset")
    total_count = cur.fetchone()[0]
    print(f"\n✓ Upload completed! Total rows in table: {total_count}")

    # 샘플 데이터 조회
    print("\nSample data:")
    cur.execute("SELECT img_url, split, filename FROM cord_dataset LIMIT 3")
    for row in cur.fetchall():
        print(f"  {row[1]}: {row[2]} -> {row[0]}")

    # 연결 종료
    cur.close()
    conn.close()
    print("\n✓ Connection closed")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 upload_to_neon.py <connection-string>")
        print("\nExample:")
        print('  python3 upload_to_neon.py "postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require"')
        print("\nYou can get your connection string from:")
        print("  https://console.neon.tech -> Your Project -> Connection Details")
        sys.exit(1)

    connection_string = sys.argv[1]
    upload_to_neon(connection_string)

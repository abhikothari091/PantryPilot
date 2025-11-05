from sqlalchemy import create_engine, text
import pandas as pd
from scripts.config import DB_URL, RAW_PATH
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

def ingest_table(table_name):
    engine = create_engine(DB_URL)
    query = text(f"SELECT * FROM {table_name}")
    # SQLAlchemy 1.4 compatibility: use connection context manager
    with engine.begin() as connection:
        result = connection.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    out_path = RAW_PATH / f"{table_name}.csv"
    df.to_csv(out_path, index=False)
    print(f"[INGEST] {table_name} → {out_path} ({len(df)} rows)")
    return df

if __name__ == "__main__":
    ingest_table("inventory")
    ingest_table("purchase_history")
    ingest_table("cord_dataset")

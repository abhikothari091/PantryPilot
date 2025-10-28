from sqlalchemy import create_engine
import pandas as pd
from scripts.config import DB_URL, RAW_PATH

def ingest_table(table_name):
    engine = create_engine(DB_URL)
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, engine)
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    out_path = RAW_PATH / f"{table_name}.csv"
    df.to_csv(out_path, index=False)
    print(f"[INGEST] {table_name} → {out_path} ({len(df)} rows)")
    return df

if __name__ == "__main__":
    ingest_table("inventory")
    ingest_table("purchase_history")
    ingest_table("cord_dataset")

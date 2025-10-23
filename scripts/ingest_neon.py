from sqlalchemy import create_engine
import pandas as pd
from scripts.config import DB_URL, RAW_PATH
import os

def ingest_table(table_name):
    engine = create_engine(DB_URL)
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, engine)
    os.makedirs(RAW_PATH, exist_ok=True)
    df.to_csv(f"{RAW_PATH}{table_name}.csv", index=False)
    print(f"[INGEST] {table_name} → {RAW_PATH}{table_name}.csv ({len(df)} rows)")
    return df

if __name__ == "__main__":
    ingest_table("inventory")
    ingest_table("purchase_history")
    ingest_table("cord_dataset")
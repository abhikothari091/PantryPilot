import pandas as pd
from scripts.utils_pint import to_canonical
from scripts.config import RAW_PATH, PROCESSED_PATH

def transform_inventory():
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW_PATH / "inventory.csv")

    # Normalize units
    df[["qty_canonical", "canonical_unit"]] = df.apply(
        lambda row: pd.Series(to_canonical(row["quantity"], row["unit"])), axis=1
    )

    # Compute stock value
    df["stock_value"] = df["qty_canonical"] * df["unit_cost"]

    # Add flag for low stock
    df["is_low_stock"] = df["qty_canonical"] < df["reorder_threshold"]

    df.to_csv(PROCESSED_PATH / "inventory_cleaned.csv", index=False)
    print("[TRANSFORM] inventory_cleaned.csv saved.")

def transform_purchases():
    df = pd.read_csv(RAW_PATH / "purchase_history.csv")
    df["unit_price"] = df["price_total"] / df["quantity_purchased"].replace(0, 1)
    df.to_csv(PROCESSED_PATH / "purchase_history_cleaned.csv", index=False)
    print("[TRANSFORM] purchase_history_cleaned.csv saved.")

if __name__ == "__main__":
    transform_inventory()
    transform_purchases()

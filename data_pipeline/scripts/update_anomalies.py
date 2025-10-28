import pandas as pd
from datetime import date
from scripts.config import PROCESSED_PATH, ALERT_PATH
from scripts.logging_conf import get_logger

log = get_logger(__name__)

def detect_anomalies():
    ALERT_PATH.mkdir(parents=True, exist_ok=True)
    inv_path = PROCESSED_PATH / "inventory_cleaned.csv"
    if not inv_path.exists():
        raise FileNotFoundError("Run transform_data.py first.")

    df = pd.read_csv(inv_path, parse_dates=["expiry_date"], dayfirst=False)
    alerts = []

    # Low stock
    low = df[df["is_low_stock"] == True]
    for _, r in low.iterrows():
        alerts.append({"item_name": r["item_name"], "issue_type": "LOW_STOCK",
                       "quantity": r["qty_canonical"], "expiry_date": r.get("expiry_date")})

    # Expired
    today = pd.to_datetime(date.today())
    exp = df[(~df["expiry_date"].isna()) & (df["expiry_date"] < today)]
    for _, r in exp.iterrows():
        alerts.append({"item_name": r["item_name"], "issue_type": "EXPIRED",
                       "quantity": r["qty_canonical"], "expiry_date": r["expiry_date"].date()})

    out = pd.DataFrame(alerts)
    out_path = ALERT_PATH / "alerts.csv"
    out.to_csv(out_path, index=False)
    log.info(f"[ALERTS] wrote {out_path} with {len(out)} rows")

if __name__ == "__main__":
    detect_anomalies()

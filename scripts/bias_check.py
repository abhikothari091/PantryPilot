import pandas as pd
from pathlib import Path
from scripts.config import RAW_PATH
from scripts.logging_conf import get_logger
log = get_logger(__name__)

SLICES = ["category", "unit"]  # adjust to your columns
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

def bias_checks():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ph = pd.read_csv(RAW_PATH / "purchase_history.csv")
    issues = []

    # Representation: min slice count threshold
    for col in SLICES:
        if col in ph.columns:
            counts = ph[col].value_counts(dropna=False)
            under = counts[counts < max(5, 0.02 * len(ph))]  # <2% or <5 rows
            for k, v in under.items():
                issues.append({"slice": col, "value": k, "issue": "underrepresented", "count": int(v)})

    # Disparity: unit_price per slice (IQR outliers)
    if {"price_total", "quantity_purchased"}.issubset(ph.columns):
        ph["unit_price"] = ph["price_total"] / ph["quantity_purchased"].replace(0, pd.NA)
        for col in SLICES:
            if col in ph.columns:
                stats = ph.groupby(col)["unit_price"].describe(percentiles=[.25,.5,.75]).reset_index()
                stats.to_csv(REPORTS_DIR / f"bias_{col}_unit_price_stats.csv", index=False)

    findings_path = REPORTS_DIR / "bias_findings.csv"
    pd.DataFrame(issues).to_csv(findings_path, index=False)
    log.info(f"Bias checks complete: {findings_path}")

if __name__ == "__main__":
    bias_checks()

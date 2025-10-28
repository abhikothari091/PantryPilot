import pandas as pd
from pathlib import Path
from scripts.config import RAW_PATH
from scripts.logging_conf import get_logger
log = get_logger(__name__)

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

def quick_stats():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for name in ["inventory.csv", "purchase_history.csv"]:
        p = RAW_PATH / name
        df = pd.read_csv(p)
        prof = df.describe(include="all")
        out_path = REPORTS_DIR / f"{name.replace('.csv','')}_stats.csv"
        prof.to_csv(out_path)
        log.info(f"Wrote {out_path}")

if __name__ == "__main__":
    quick_stats()

import json
from pathlib import Path

import pandas as pd

from .config import PROJECT_ROOT


REPORTS_DIR = PROJECT_ROOT / "model_development" / "llm_eval" / "reports"


def _latest_file(pattern: str) -> Path:
    candidates = sorted(REPORTS_DIR.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No files matching {pattern} in {REPORTS_DIR}")
    return candidates[-1]


def load_latest_eval_summary() -> pd.DataFrame:
    """Load the latest eval_summary_*.csv as a DataFrame."""
    latest_csv = _latest_file("eval_summary_*.csv")
    print(f"[INFO] Using eval summary: {latest_csv}")
    return pd.read_csv(latest_csv)


def load_latest_eval_json() -> dict:
    """Load the latest eval_*.json (full metrics dict)."""
    latest_json = _latest_file("eval_*.json")
    print(f"[INFO] Using eval JSON: {latest_json}")
    with open(latest_json, "r") as f:
        return json.load(f)


def load_bias_report() -> pd.DataFrame:
    """Load bias_report.csv if it exists."""
    path = REPORTS_DIR / "bias_report.csv"
    if not path.exists():
        raise FileNotFoundError(f"bias_report.csv not found in {REPORTS_DIR}")
    print(f"[INFO] Using bias report: {path}")
    return pd.read_csv(path)


def summarize_eval(df: pd.DataFrame) -> None:
    """Print a compact comparison between base and lora models."""
    print("\n=== Main Evaluation (recipes_test) ===")

    # Split model/temperature cleanly if needed
    # We already have 'model' and 'temperature' columns in eval_summary_*.
    cols = [c for c in df.columns if c not in {"model", "temperature"}]

    # Focus on the main metrics
    focus_metrics = [
        "json_valid_rate",
        "diet_match_rate",
        "constraint_violation_rate",
        "cuisine_match_rate",
        "inventory_coverage_mean",
    ]
    focus_metrics = [m for m in focus_metrics if m in df.columns]

    # Pivot: rows = model, cols = metric (filter to temp=0.7 by default)
    if "temperature" in df.columns:
        df_temp = df[df["temperature"] == 0.7].copy()
    else:
        df_temp = df.copy()

    if df_temp.empty:
        print("[WARN] No rows found for temperature=0.7; using all temperatures.")
        df_temp = df

    summary = (
        df_temp.groupby("model")[focus_metrics]
        .mean()
        .sort_index()
    )

    print("\n[Eval] Base vs LoRA @ temperature=0.7")
    print(summary.to_markdown(floatfmt=".3f"))


def summarize_bias(df_bias: pd.DataFrame) -> None:
    """Print slice-based comparison for bias report."""
    print("\n=== Bias Evaluation (val_bias) ===")

    required_cols = {"model", "preference", "cuisine", "n"}
    missing = required_cols - set(df_bias.columns)
    if missing:
        print(f"[WARN] Bias report missing columns: {missing}")

    focus_metrics = [
        "json_valid_rate",
        "diet_match_rate",
        "constraint_violation_rate",
        "inventory_coverage_mean",
    ]
    focus_metrics = [m for m in focus_metrics if m in df_bias.columns]

    # Aggregate by model + preference
    pref_summary = (
        df_bias.groupby(["model", "preference"])[focus_metrics + ["n"]]
        .mean()
        .sort_values(["model", "preference"])
    )

    print("\n[Bias] By model × dietary preference")
    print(pref_summary.to_markdown(floatfmt=".3f"))

    # Aggregate by model + cuisine
    if "cuisine" in df_bias.columns:
        cuis_summary = (
            df_bias.groupby(["model", "cuisine"])[focus_metrics + ["n"]]
            .mean()
            .sort_values(["model", "cuisine"])
        )
        print("\n[Bias] By model × cuisine")
        print(cuis_summary.to_markdown(floatfmt=".3f"))


def main():
    # Main eval
    eval_df = load_latest_eval_summary()
    summarize_eval(eval_df)

    # Bias eval (optional)
    try:
        bias_df = load_bias_report()
        summarize_bias(bias_df)
    except FileNotFoundError as e:
        print(f"[WARN] {e}")
        print("[WARN] Run bias_eval.py first to generate bias_report.csv")


if __name__ == "__main__":
    main()
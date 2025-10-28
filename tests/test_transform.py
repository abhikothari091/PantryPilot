import os, pandas as pd
from scripts.utils_pint import to_canonical

def test_can_compute_stock_value(tmp_path):
    df = pd.DataFrame([{"quantity": 0.5, "unit": "kg", "unit_cost": 10.0, "reorder_threshold": 300}])
    df[["qty_canonical", "canonical_unit"]] = df.apply(
        lambda r: pd.Series(to_canonical(r["quantity"], r["unit"])), axis=1)
    df["stock_value"] = df["qty_canonical"] * df["unit_cost"]
    assert df.loc[0, "stock_value"] == 500 * 10.0
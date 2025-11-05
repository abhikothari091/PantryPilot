import os
import pkgutil
import pytest

DAG_PATH = os.path.join("airflow", "dags", "pantry_pilot_dag.py")

@pytest.mark.skipif(
    "apache_airflow" not in {module.name.replace("-", "_") for module in pkgutil.iter_modules()},
    reason="Airflow not installed in this environment",
)
def test_dag_imports_without_errors():
    # Importing via runpy avoids adding to sys.path permanently
    import runpy
    assert os.path.exists(DAG_PATH), "DAG file not found"
    runpy.run_path(DAG_PATH, run_name="__main__")

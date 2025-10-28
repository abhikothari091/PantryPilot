from datetime import datetime
from pathlib import Path
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "pantrypilot",
    "retries": 1,
}

# Get the data_pipeline directory (two levels up from this DAG file)
DAG_DIR = Path(__file__).parent
DATA_PIPELINE_DIR = DAG_DIR.parent.parent

with DAG(
    dag_id="pantrypilot_data_pipeline",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # trigger manually; set "0 6 * * *" for daily
    catchup=False,
    tags=["pantrypilot", "data-pipeline"],
) as dag:

    # Use environment's python and dvc (assumes virtual environment is activated)
    ingest = BashOperator(
        task_id="ingest_neon",
        bash_command=f"cd {DATA_PIPELINE_DIR} && python -m scripts.ingest_neon"
    )

    validate = BashOperator(
        task_id="validate_data",
        bash_command=f"cd {DATA_PIPELINE_DIR} && python -m scripts.validate_data"
    )

    transform = BashOperator(
        task_id="transform_data",
        bash_command=f"cd {DATA_PIPELINE_DIR} && python -m scripts.transform_data"
    )

    anomalies = BashOperator(
        task_id="detect_anomalies",
        bash_command=f"cd {DATA_PIPELINE_DIR} && python -m scripts.update_anomalies"
    )

    dvc_add = BashOperator(
        task_id="dvc_add_and_push",
        bash_command=f"cd {DATA_PIPELINE_DIR} && dvc add data/raw data/processed data/alerts && dvc push"
    )

    ingest >> validate >> transform >> anomalies >> dvc_add
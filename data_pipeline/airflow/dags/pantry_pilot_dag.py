from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "pantrypilot",
    "retries": 1,
}

with DAG(
    dag_id="pantrypilot_data_pipeline",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # trigger manually; set "0 6 * * *" for daily
    catchup=False,
    tags=["pantrypilot", "data-pipeline"],
) as dag:

    ingest = BashOperator(
        task_id="ingest_neon",
        bash_command="cd /opt/airflow/Data_Pipeline && python -m scripts.ingest_neon"
    )

    validate = BashOperator(
        task_id="validate_data",
        bash_command="cd /opt/airflow/Data_Pipeline && python -m scripts.validate_data"
    )

    transform = BashOperator(
        task_id="transform_data",
        bash_command="cd /opt/airflow/Data_Pipeline && python -m scripts.transform_data"
    )

    anomalies = BashOperator(
        task_id="detect_anomalies",
        bash_command="cd /opt/airflow/Data_Pipeline && python -m scripts.update_anomalies"
    )

    dvc_track = BashOperator(
        task_id="dvc_status",
        bash_command="cd /opt/airflow/Data_Pipeline && dvc status"
    )

    ingest >> validate >> transform >> anomalies >> dvc_track
from great_expectations.data_context import FileDataContext
from great_expectations.checkpoint import SimpleCheckpoint
import os
import csv
from datetime import datetime

def save_summary(dataset, suite, success):
    """Append validation results to a CSV summary log."""
    os.makedirs("reports", exist_ok=True)
    with open("reports/validation_summary.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), dataset, suite, "PASS" if success else "FAIL"])

def run_validation():
    context = FileDataContext(context_root_dir="great_expectations")
    data_path = "data/raw"

    datasets = [
        ("inventory.csv", "inventory_suite"),
        ("purchase_history.csv", "purchase_history_suite"),
    ]

    for filename, suite_name in datasets:
        checkpoint = SimpleCheckpoint(
            name=f"{suite_name}_checkpoint",
            data_context=context,
            validations=[
                {
                    "batch_request": {
                        "runtime_parameters": {"path": os.path.join(data_path, filename)},
                        "batch_identifiers": {"default_identifier_name": "default_id"},
                        "datasource_name": "data_dir",
                        "data_connector_name": "default_runtime_data_connector_name",
                        "data_asset_name": filename,
                    },
                    "expectation_suite_name": suite_name,
                }
            ],
        )

        print(f"[VALIDATION] Running suite '{suite_name}' on {filename} ...")
        result = checkpoint.run()
        print(f"[VALIDATION] {filename} → {'PASS' if result['success'] else 'FAIL'}")

        # Log the result
        save_summary(filename, suite_name, result["success"])

if __name__ == "__main__":
    run_validation()
"""
Manual registration + validation helper for new model versions.

Flow:
- Optionally run lightweight eval + bias eval from model_development.llm_eval
- Record a registry entry with version metadata and paths to latest reports

Intended to be run after manual DPO training + redeploy.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
LLM_EVAL_REPORTS = PROJECT_ROOT / "model_development" / "llm_eval" / "reports"
DEFAULT_REGISTRY = PROJECT_ROOT / "model_deployment" / "model_registry" / "registry.json"


def run(cmd) -> int:
    """Run a shell command and stream output."""
    print(f"▶️  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def latest_file(prefix: str, suffix: str) -> Optional[Path]:
    if not LLM_EVAL_REPORTS.exists():
        return None
    candidates = sorted(
        LLM_EVAL_REPORTS.glob(f"{prefix}*{suffix}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_registry(path: Path) -> Dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"models": []}


def save_registry(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"📝 Registry updated at {path}")


def main():
    parser = argparse.ArgumentParser(description="Register and validate a model version.")
    parser.add_argument("--version", required=True, help="Version tag, e.g., dpo-v1.1")
    parser.add_argument("--artifact", required=True, help="Path/URI to the deployed model or adapter.")
    parser.add_argument("--notes", default="", help="Optional notes (e.g., commit hash, persona).")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Registry JSON path.")
    parser.add_argument(
        "--run-eval",
        action="store_true",
        help="Run lightweight eval + bias eval (limited examples) before registering.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=5,
        help="Number of examples for quick eval when --run-eval is set.",
    )
    args = parser.parse_args()

    eval_summary_path = None
    bias_report_path = None

    if args.run_eval:
        # Run tiny evals to keep runtime reasonable; adjust flags here if needed.
        eval_cmd = [
            sys.executable,
            "-m",
            "model_development.llm_eval.run_eval",
            "--max-examples",
            str(args.max_examples),
            "--temperatures",
            "0.7",
        ]
        bias_cmd = [
            sys.executable,
            "-m",
            "model_development.llm_eval.bias_eval",
            "--temperature",
            "0.7",
            "--max-examples",
            str(args.max_examples),
        ]

        if run(eval_cmd) != 0:
            print("⚠️ run_eval failed; registry entry will still be written without eval paths.")
        if run(bias_cmd) != 0:
            print("⚠️ bias_eval failed; registry entry will still be written without bias paths.")

        eval_summary = latest_file("eval_summary_", ".csv")
        bias_report = latest_file("bias_report", ".csv")
        eval_summary_path = str(eval_summary) if eval_summary else None
        bias_report_path = str(bias_report) if bias_report else None

    registry = load_registry(args.registry)
    entry = {
        "version": args.version,
        "artifact": args.artifact,
        "notes": args.notes,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "eval_summary": eval_summary_path,
        "bias_report": bias_report_path,
    }
    registry["models"].append(entry)
    save_registry(args.registry, registry)

    print("✅ Registered model version:")
    print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()

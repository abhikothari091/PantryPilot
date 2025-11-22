#!/usr/bin/env python3
"""
DPO Persona Model Evaluation Script

Evaluates DPO-trained persona models against SFT baseline using Vertex AI.
Supports multiple evaluator models (Claude, Gemini) for cross-validation.

Usage:
    python evaluate_dpo_personas.py --personas all --count 20 --evaluators all
    python evaluate_dpo_personas.py --personas persona_a_korean_spicy --count 10
"""

import argparse
import json
import yaml
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from vertexai_evaluator import VertexAIEvaluator, MultiModelEvaluator
from model_loader import SequentialModelLoader
from report_generator import ReportGenerator


class DPOEvaluationRunner:
    """
    Main evaluation runner for DPO persona models
    """

    def __init__(
        self,
        project_id: str,
        sft_adapter_path: str,
        dpo_models_dir: str,
        personas_file: str,
        test_cases_file: str,
        output_dir: str = "evaluation/reports"
    ):
        """
        Initialize evaluation runner

        Args:
            project_id: GCP project ID for Vertex AI
            sft_adapter_path: Path to SFT LoRA adapter
            dpo_models_dir: Directory with DPO persona models
            personas_file: Path to personas.yaml
            test_cases_file: Path to test_cases.yaml
            output_dir: Output directory for results
        """
        self.project_id = project_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load personas
        with open(personas_file) as f:
            self.personas = yaml.safe_load(f)['personas']

        # Load test cases
        with open(test_cases_file) as f:
            self.test_cases = yaml.safe_load(f)['test_cases']

        # Initialize model loader
        print("\n" + "="*70)
        print("🚀 Initializing DPO Evaluation System")
        print("="*70)

        self.model_loader = SequentialModelLoader(
            base_model_id="meta-llama/Llama-3.2-3B-Instruct",
            sft_adapter_path=sft_adapter_path,
            dpo_models_dir=dpo_models_dir
        )

        # Load tokenizer
        self.model_loader.load_tokenizer()

        # Initialize evaluators
        self.evaluators = {}

        print(f"\n✅ Loaded {len(self.personas)} personas")
        print(f"✅ Loaded {sum(len(cases) for cases in self.test_cases.values())} total test cases")

    def add_evaluator(self, name: str, model: str):
        """Add a Vertex AI evaluator"""
        evaluator = VertexAIEvaluator(
            project_id=self.project_id,
            location="us-central1",
            evaluator_model=model
        )
        self.evaluators[name] = evaluator
        return evaluator

    def run_evaluation(
        self,
        persona_ids: List[str],
        test_count: int = 20,
        evaluator_names: List[str] = None,
        skip_generation: bool = False,
        generation_cache_file: str = None
    ) -> Dict:
        """
        Run full evaluation

        Args:
            persona_ids: List of persona IDs to evaluate
            test_count: Number of test cases per persona (max 20)
            evaluator_names: List of evaluator names to use
            skip_generation: Skip recipe generation, load from cache
            generation_cache_file: Cache file for generated recipes

        Returns:
            Dictionary with all evaluation results
        """
        if evaluator_names is None:
            evaluator_names = list(self.evaluators.keys())

        all_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "project_id": self.project_id,
                "personas_evaluated": persona_ids,
                "test_count_per_persona": test_count,
                "evaluators_used": evaluator_names,
                "total_tests": len(persona_ids) * test_count
            },
            "persona_results": {}
        }

        # Step 1: Generate recipes (SFT vs DPO)
        if not skip_generation:
            print("\n" + "="*70)
            print("📝 Step 1: Generating Recipes (SFT vs DPO)")
            print("="*70)

            generated_recipes = self._generate_all_recipes(persona_ids, test_count)

            # Save generation cache
            if generation_cache_file:
                cache_path = self.output_dir / generation_cache_file
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(generated_recipes, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Saved generation cache to: {cache_path}")
        else:
            # Load from cache
            if not generation_cache_file:
                raise ValueError("Must provide generation_cache_file when skip_generation=True")

            cache_path = self.output_dir / generation_cache_file
            with open(cache_path, encoding='utf-8') as f:
                generated_recipes = json.load(f)
            print(f"\n📂 Loaded generation cache from: {cache_path}")

        # Step 2: Evaluate with Vertex AI models
        print("\n" + "="*70)
        print("🤖 Step 2: Evaluating with Vertex AI Models")
        print("="*70)

        for persona_id in persona_ids:
            print(f"\n{'='*70}")
            print(f"📊 Evaluating: {self.personas[persona_id]['name']}")
            print(f"{'='*70}")

            persona_generated = generated_recipes[persona_id]
            persona_config = self.personas[persona_id]

            # Evaluate with each evaluator
            evaluations = {}
            for eval_name in evaluator_names:
                print(f"\n🔍 Evaluator: {eval_name}")
                evaluator = self.evaluators[eval_name]

                eval_results = []
                for i, test_data in enumerate(tqdm(persona_generated, desc=f"  {eval_name}")):
                    evaluation = evaluator.evaluate_recipe_pair(
                        persona_config=persona_config,
                        recipe_sft=test_data['sft_recipe'],
                        recipe_dpo=test_data['dpo_recipe'],
                        inventory=test_data['inventory'],
                        user_request=test_data['user_request']
                    )

                    eval_results.append({
                        "test_case_id": test_data['test_case_id'],
                        "category": test_data['category'],
                        "evaluation": evaluation
                    })

                evaluations[eval_name] = eval_results

            # Compute consensus across evaluators
            consensus = self._compute_consensus(evaluations)

            all_results["persona_results"][persona_id] = {
                "persona_name": persona_config['name'],
                "test_count": len(persona_generated),
                "evaluations": evaluations,
                "consensus": consensus,
                "generated_recipes": persona_generated
            }

        # Step 3: Compute summary statistics
        print("\n" + "="*70)
        print("📈 Step 3: Computing Summary Statistics")
        print("="*70)

        summary = self._compute_summary(all_results)
        all_results["summary"] = summary

        self._print_summary(summary)

        return all_results

    def _generate_all_recipes(self, persona_ids: List[str], test_count: int) -> Dict:
        """Generate recipes for all personas and test cases"""
        generated_recipes = {}

        for persona_id in persona_ids:
            print(f"\n{'='*70}")
            print(f"Generating recipes for: {self.personas[persona_id]['name']}")
            print(f"{'='*70}")

            persona_config = self.personas[persona_id]
            test_cases = self.test_cases[persona_id][:test_count]

            persona_recipes = []

            for i, test_case in enumerate(tqdm(test_cases, desc=f"  {persona_id}")):
                print(f"\n  Test {i+1}/{len(test_cases)}: {test_case['request'][:50]}...")

                # Generate with both models
                sft_recipe, dpo_recipe = self.model_loader.compare_models(
                    persona_id=persona_id,
                    persona_config=persona_config,
                    inventory=test_case['inventory'],
                    user_request=test_case['request'],
                    max_new_tokens=512,
                    temperature=0.7
                )

                persona_recipes.append({
                    "test_case_id": test_case['id'],
                    "category": test_case['category'],
                    "inventory": test_case['inventory'],
                    "user_request": test_case['request'],
                    "sft_recipe": sft_recipe,
                    "dpo_recipe": dpo_recipe,
                    "note": test_case.get('note', '')
                })

            generated_recipes[persona_id] = persona_recipes

        return generated_recipes

    def _compute_consensus(self, evaluations: Dict[str, List[Dict]]) -> Dict:
        """Compute consensus across multiple evaluators"""
        if not evaluations:
            return {"error": "No evaluations provided"}

        # Get test count
        test_count = len(next(iter(evaluations.values())))

        consensus_results = []

        for test_idx in range(test_count):
            # Get all evaluations for this test
            test_evaluations = {
                eval_name: evals[test_idx]["evaluation"]
                for eval_name, evals in evaluations.items()
            }

            # Count votes
            winners = [e["winner"] for e in test_evaluations.values() if e["winner"] != "unknown"]

            if winners:
                sft_votes = winners.count("sft")
                dpo_votes = winners.count("dpo")

                if sft_votes > dpo_votes:
                    consensus_winner = "sft"
                    confidence = "high" if sft_votes == len(winners) else "medium"
                elif dpo_votes > sft_votes:
                    consensus_winner = "dpo"
                    confidence = "high" if dpo_votes == len(winners) else "medium"
                else:
                    consensus_winner = "tie"
                    confidence = "low"

                consensus_results.append({
                    "test_idx": test_idx,
                    "winner": consensus_winner,
                    "confidence": confidence,
                    "votes": {"sft": sft_votes, "dpo": dpo_votes},
                    "agreement_rate": max(sft_votes, dpo_votes) / len(winners)
                })
            else:
                consensus_results.append({
                    "test_idx": test_idx,
                    "winner": "unknown",
                    "confidence": "none",
                    "votes": {"sft": 0, "dpo": 0},
                    "agreement_rate": 0
                })

        # Compute overall consensus stats
        total_dpo_wins = sum(1 for r in consensus_results if r["winner"] == "dpo")
        total_sft_wins = sum(1 for r in consensus_results if r["winner"] == "sft")
        total_ties = sum(1 for r in consensus_results if r["winner"] == "tie")

        return {
            "test_results": consensus_results,
            "overall": {
                "dpo_wins": total_dpo_wins,
                "sft_wins": total_sft_wins,
                "ties": total_ties,
                "total_tests": test_count,
                "dpo_win_rate": total_dpo_wins / test_count if test_count > 0 else 0,
                "avg_agreement_rate": sum(r["agreement_rate"] for r in consensus_results) / test_count if test_count > 0 else 0
            }
        }

    def _compute_summary(self, all_results: Dict) -> Dict:
        """Compute overall summary statistics"""
        total_tests = 0
        total_dpo_wins = 0
        total_sft_wins = 0
        total_ties = 0

        per_persona_stats = {}

        for persona_id, persona_data in all_results["persona_results"].items():
            consensus = persona_data["consensus"]["overall"]

            total_tests += consensus["total_tests"]
            total_dpo_wins += consensus["dpo_wins"]
            total_sft_wins += consensus["sft_wins"]
            total_ties += consensus["ties"]

            per_persona_stats[persona_id] = {
                "name": persona_data["persona_name"],
                "dpo_win_rate": consensus["dpo_win_rate"],
                "dpo_wins": consensus["dpo_wins"],
                "sft_wins": consensus["sft_wins"],
                "ties": consensus["ties"],
                "total_tests": consensus["total_tests"]
            }

        return {
            "total_tests": total_tests,
            "dpo_wins": total_dpo_wins,
            "sft_wins": total_sft_wins,
            "ties": total_ties,
            "dpo_win_rate": total_dpo_wins / total_tests if total_tests > 0 else 0,
            "sft_win_rate": total_sft_wins / total_tests if total_tests > 0 else 0,
            "tie_rate": total_ties / total_tests if total_tests > 0 else 0,
            "per_persona": per_persona_stats
        }

    def _print_summary(self, summary: Dict):
        """Print summary statistics"""
        print(f"\n{'='*70}")
        print("📊 EVALUATION SUMMARY")
        print(f"{'='*70}")
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"DPO Wins: {summary['dpo_wins']} ({summary['dpo_win_rate']*100:.1f}%)")
        print(f"SFT Wins: {summary['sft_wins']} ({summary['sft_win_rate']*100:.1f}%)")
        print(f"Ties: {summary['ties']} ({summary['tie_rate']*100:.1f}%)")

        print(f"\n{'='*70}")
        print("Per-Persona Results:")
        print(f"{'='*70}")

        for persona_id, stats in summary['per_persona'].items():
            print(f"\n{stats['name']} ({persona_id}):")
            print(f"  DPO Win Rate: {stats['dpo_win_rate']*100:.1f}% ({stats['dpo_wins']}/{stats['total_tests']})")
            print(f"  SFT Wins: {stats['sft_wins']}, Ties: {stats['ties']}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate DPO persona models using Vertex AI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--project_id", required=True, help="GCP project ID")
    parser.add_argument("--personas", default="all", help="Comma-separated persona IDs or 'all'")
    parser.add_argument("--count", type=int, default=20, help="Test cases per persona (max 20)")
    parser.add_argument("--evaluators", default="all", help="Comma-separated evaluator names or 'all'")
    parser.add_argument("--sft_adapter", default="models/llama3b_lambda_lora", help="Path to SFT adapter")
    parser.add_argument("--dpo_models", default="models/dpo_personas", help="Path to DPO models directory")
    parser.add_argument("--personas_file", default="data_pipeline/05_dpo_training/personas.yaml")
    parser.add_argument("--test_cases_file", default="evaluation/test_cases.yaml")
    parser.add_argument("--output_dir", default="evaluation/reports", help="Output directory")
    parser.add_argument("--skip_generation", action="store_true", help="Skip recipe generation, use cache")
    parser.add_argument("--generation_cache", default="generation_cache.json", help="Cache file name")

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent
    sft_path = project_root / args.sft_adapter
    dpo_path = project_root / args.dpo_models
    personas_file = project_root / args.personas_file
    test_cases_file = project_root / args.test_cases_file

    # Initialize runner
    runner = DPOEvaluationRunner(
        project_id=args.project_id,
        sft_adapter_path=str(sft_path),
        dpo_models_dir=str(dpo_path),
        personas_file=str(personas_file),
        test_cases_file=str(test_cases_file),
        output_dir=args.output_dir
    )

    # Add evaluators
    if args.evaluators == "all":
        runner.add_evaluator("gemini-flash", "gemini-flash")
        runner.add_evaluator("claude-haiku", "claude-haiku")
        runner.add_evaluator("claude-sonnet", "claude-sonnet")
    else:
        for eval_name in args.evaluators.split(","):
            eval_name = eval_name.strip()
            runner.add_evaluator(eval_name, eval_name)

    # Determine personas to evaluate
    if args.personas == "all":
        persona_ids = list(runner.personas.keys())
    else:
        persona_ids = [p.strip() for p in args.personas.split(",")]

    # Validate persona IDs
    for pid in persona_ids:
        if pid not in runner.personas:
            print(f"Error: Unknown persona '{pid}'")
            print(f"Available: {list(runner.personas.keys())}")
            return

    # Run evaluation
    results = runner.run_evaluation(
        persona_ids=persona_ids,
        test_count=args.count,
        skip_generation=args.skip_generation,
        generation_cache_file=args.generation_cache
    )

    # Save detailed results
    output_path = runner.output_dir / "detailed_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved detailed results to: {output_path}")

    # Save summary
    summary_path = runner.output_dir / "summary_stats.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results["summary"], f, indent=2, ensure_ascii=False)
    print(f"💾 Saved summary to: {summary_path}")

    # Generate HTML report
    print(f"\n📄 Generating HTML report...")
    report_gen = ReportGenerator(results, runner.personas)
    html_path = runner.output_dir / "evaluation_report.html"
    report_gen.generate_html_report(str(html_path))
    print(f"💾 Saved HTML report to: {html_path}")

    print(f"\n{'='*70}")
    print("✅ Evaluation Complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

"""
Report Generator for DPO Evaluation Results

Generates HTML reports with visualizations and JSON summaries.
"""

import json
from typing import Dict, List
from pathlib import Path
from datetime import datetime


class ReportGenerator:
    """
    Generate evaluation reports in HTML and JSON formats
    """

    def __init__(self, evaluation_results: Dict, personas: Dict):
        """
        Initialize report generator

        Args:
            evaluation_results: Results from DPOEvaluationRunner
            personas: Personas configuration dictionary
        """
        self.results = evaluation_results
        self.personas = personas
        self.metadata = evaluation_results.get("metadata", {})
        self.summary = evaluation_results.get("summary", {})
        self.persona_results = evaluation_results.get("persona_results", {})

    def generate_html_report(self, output_path: str):
        """
        Generate HTML report with visualizations

        Args:
            output_path: Path to save HTML file
        """
        html = self._build_html()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Generated HTML report: {output_path}")

    def _build_html(self) -> str:
        """Build complete HTML report"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DPO Persona Evaluation Report</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._build_header()}
        {self._build_overall_summary()}
        {self._build_per_persona_results()}
        {self._build_detailed_evaluations()}
        {self._build_footer()}
    </div>
</body>
</html>"""

    def _get_css(self) -> str:
        """Get CSS styles"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }

        h1, h2, h3 {
            color: #2c3e50;
            margin-bottom: 20px;
        }

        h1 {
            font-size: 2.5em;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }

        h2 {
            font-size: 1.8em;
            margin-top: 40px;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 10px;
        }

        h3 {
            font-size: 1.3em;
            color: #34495e;
        }

        .metadata {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }

        .metadata p {
            margin: 5px 0;
        }

        .summary-box {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .stat-card.dpo-win {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }

        .stat-card.sft-win {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }

        .stat-card.tie {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        .stat-value {
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }

        .stat-label {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .persona-section {
            background-color: #f8f9fa;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px;
            border-left: 5px solid #3498db;
        }

        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 15px 0;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            float: left;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }

        .progress-dpo {
            background-color: #27ae60;
        }

        .progress-sft {
            background-color: #e74c3c;
        }

        .progress-tie {
            background-color: #9b59b6;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        th {
            background-color: #34495e;
            color: white;
            font-weight: bold;
        }

        tr:hover {
            background-color: #f5f5f5;
        }

        .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
        }

        .badge-dpo {
            background-color: #27ae60;
            color: white;
        }

        .badge-sft {
            background-color: #e74c3c;
            color: white;
        }

        .badge-tie {
            background-color: #9b59b6;
            color: white;
        }

        .badge-high {
            background-color: #2ecc71;
            color: white;
        }

        .badge-medium {
            background-color: #f39c12;
            color: white;
        }

        .badge-low {
            background-color: #e67e22;
            color: white;
        }

        .evaluator-results {
            margin: 15px 0;
            padding: 15px;
            background-color: white;
            border-radius: 5px;
            border: 1px solid #ddd;
        }

        .score-display {
            display: flex;
            justify-content: space-around;
            margin: 15px 0;
        }

        .score-item {
            text-align: center;
        }

        .score-value {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }

        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
        }

        .collapsible {
            cursor: pointer;
            padding: 10px;
            background-color: #3498db;
            color: white;
            border: none;
            text-align: left;
            outline: none;
            font-size: 1em;
            border-radius: 5px;
            margin: 10px 0;
            width: 100%;
        }

        .collapsible:hover {
            background-color: #2980b9;
        }

        .collapsible-content {
            display: none;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 15px;
        }

        .test-case-detail {
            margin: 15px 0;
            padding: 15px;
            background-color: white;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }
        """

    def _build_header(self) -> str:
        """Build report header"""
        timestamp = self.metadata.get("timestamp", "Unknown")
        project_id = self.metadata.get("project_id", "Unknown")
        total_tests = self.metadata.get("total_tests", 0)
        evaluators = ", ".join(self.metadata.get("evaluators_used", []))

        return f"""
        <header>
            <h1>🎭 DPO Persona Model Evaluation Report</h1>
            <div class="metadata">
                <p><strong>Generated:</strong> {timestamp}</p>
                <p><strong>GCP Project:</strong> {project_id}</p>
                <p><strong>Total Tests:</strong> {total_tests}</p>
                <p><strong>Evaluators Used:</strong> {evaluators}</p>
            </div>
        </header>
        """

    def _build_overall_summary(self) -> str:
        """Build overall summary section"""
        total_tests = self.summary.get("total_tests", 0)
        dpo_wins = self.summary.get("dpo_wins", 0)
        sft_wins = self.summary.get("sft_wins", 0)
        ties = self.summary.get("ties", 0)
        dpo_win_rate = self.summary.get("dpo_win_rate", 0) * 100

        dpo_pct = (dpo_wins / total_tests * 100) if total_tests > 0 else 0
        sft_pct = (sft_wins / total_tests * 100) if total_tests > 0 else 0
        tie_pct = (ties / total_tests * 100) if total_tests > 0 else 0

        return f"""
        <section id="overall-summary">
            <h2>📊 Overall Summary</h2>

            <div class="summary-box">
                <div class="stat-card">
                    <div class="stat-label">Total Tests</div>
                    <div class="stat-value">{total_tests}</div>
                </div>
                <div class="stat-card dpo-win">
                    <div class="stat-label">DPO Wins</div>
                    <div class="stat-value">{dpo_wins}</div>
                    <div class="stat-label">{dpo_win_rate:.1f}% Win Rate</div>
                </div>
                <div class="stat-card sft-win">
                    <div class="stat-label">SFT Wins</div>
                    <div class="stat-value">{sft_wins}</div>
                    <div class="stat-label">{sft_pct:.1f}%</div>
                </div>
                <div class="stat-card tie">
                    <div class="stat-label">Ties</div>
                    <div class="stat-value">{ties}</div>
                    <div class="stat-label">{tie_pct:.1f}%</div>
                </div>
            </div>

            <h3>Win Rate Distribution</h3>
            <div class="progress-bar">
                <div class="progress-fill progress-dpo" style="width: {dpo_pct}%">
                    DPO: {dpo_pct:.1f}%
                </div>
                <div class="progress-fill progress-sft" style="width: {sft_pct}%">
                    SFT: {sft_pct:.1f}%
                </div>
                <div class="progress-fill progress-tie" style="width: {tie_pct}%">
                    Tie: {tie_pct:.1f}%
                </div>
            </div>
        </section>
        """

    def _build_per_persona_results(self) -> str:
        """Build per-persona results section"""
        per_persona = self.summary.get("per_persona", {})

        html = """
        <section id="per-persona-results">
            <h2>🎭 Per-Persona Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Persona</th>
                        <th>Total Tests</th>
                        <th>DPO Wins</th>
                        <th>SFT Wins</th>
                        <th>Ties</th>
                        <th>DPO Win Rate</th>
                    </tr>
                </thead>
                <tbody>
        """

        for persona_id, stats in per_persona.items():
            name = stats['name']
            total = stats['total_tests']
            dpo = stats['dpo_wins']
            sft = stats['sft_wins']
            ties = stats['ties']
            win_rate = stats['dpo_win_rate'] * 100

            html += f"""
                    <tr>
                        <td><strong>{name}</strong><br><small>{persona_id}</small></td>
                        <td>{total}</td>
                        <td><span class="badge badge-dpo">{dpo}</span></td>
                        <td><span class="badge badge-sft">{sft}</span></td>
                        <td><span class="badge badge-tie">{ties}</span></td>
                        <td><strong>{win_rate:.1f}%</strong></td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </section>
        """

        return html

    def _build_detailed_evaluations(self) -> str:
        """Build detailed evaluations section"""
        html = """
        <section id="detailed-evaluations">
            <h2>🔍 Detailed Evaluations by Persona</h2>
        """

        for persona_id, persona_data in self.persona_results.items():
            persona_name = persona_data['persona_name']
            consensus = persona_data['consensus']['overall']
            evaluations = persona_data['evaluations']

            html += f"""
            <div class="persona-section">
                <h3>{persona_name} ({persona_id})</h3>
                <p><strong>DPO Win Rate:</strong> {consensus['dpo_win_rate']*100:.1f}%
                   ({consensus['dpo_wins']}/{consensus['total_tests']} tests)</p>

                <h4>Evaluator Breakdown:</h4>
            """

            # Show results from each evaluator
            for eval_name, eval_results in evaluations.items():
                # Count wins per evaluator
                dpo_wins = sum(1 for r in eval_results if r['evaluation']['winner'] == 'dpo')
                sft_wins = sum(1 for r in eval_results if r['evaluation']['winner'] == 'sft')
                ties = sum(1 for r in eval_results if r['evaluation']['winner'] == 'tie')

                html += f"""
                <div class="evaluator-results">
                    <strong>{eval_name}</strong>:
                    DPO {dpo_wins} | SFT {sft_wins} | Tie {ties}
                </div>
                """

            # Sample test cases
            html += """
                <button class="collapsible">Show Test Case Details</button>
                <div class="collapsible-content">
            """

            # Show first 5 test cases
            generated_recipes = persona_data.get('generated_recipes', [])[:5]
            test_results = persona_data['consensus']['test_results'][:5]

            for i, (gen, test_result) in enumerate(zip(generated_recipes, test_results)):
                winner = test_result['winner']
                confidence = test_result['confidence']
                votes = test_result['votes']

                html += f"""
                <div class="test-case-detail">
                    <p><strong>Test {gen['test_case_id']}</strong> ({gen['category']})</p>
                    <p><strong>Request:</strong> {gen['user_request']}</p>
                    <p><strong>Inventory:</strong> {', '.join(gen['inventory'])}</p>
                    <p><strong>Winner:</strong> <span class="badge badge-{winner}">{winner.upper()}</span>
                       <span class="badge badge-{confidence}">{confidence}</span></p>
                    <p><strong>Votes:</strong> DPO: {votes['sft']}, SFT: {votes['dpo']}</p>
                </div>
                """

            html += """
                </div> <!-- collapsible-content -->
            </div> <!-- persona-section -->
            """

        html += """
        </section>

        <script>
        // Collapsible sections
        var coll = document.getElementsByClassName("collapsible");
        for (var i = 0; i < coll.length; i++) {
            coll[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.display === "block") {
                    content.style.display = "none";
                } else {
                    content.style.display = "block";
                }
            });
        }
        </script>
        """

        return html

    def _build_footer(self) -> str:
        """Build report footer"""
        return f"""
        <footer class="footer">
            <p>Generated by DPO Persona Evaluation System</p>
            <p>RecipeGen-LLM | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
        """


if __name__ == "__main__":
    # Test with mock data
    mock_results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "project_id": "test-project",
            "total_tests": 120,
            "evaluators_used": ["gemini-flash", "claude-haiku", "claude-sonnet"]
        },
        "summary": {
            "total_tests": 120,
            "dpo_wins": 96,
            "sft_wins": 20,
            "ties": 4,
            "dpo_win_rate": 0.8,
            "sft_win_rate": 0.167,
            "tie_rate": 0.033,
            "per_persona": {
                "persona_a_korean_spicy": {
                    "name": "Korean Food Lover (Spicy)",
                    "dpo_win_rate": 0.85,
                    "dpo_wins": 17,
                    "sft_wins": 3,
                    "ties": 0,
                    "total_tests": 20
                }
            }
        },
        "persona_results": {}
    }

    mock_personas = {}

    gen = ReportGenerator(mock_results, mock_personas)
    gen.generate_html_report("test_report.html")
    print("✅ Test report generated")
